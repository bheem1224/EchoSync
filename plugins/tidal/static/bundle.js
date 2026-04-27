//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol(), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, v = () => {};
function y(e) {
	return e();
}
function b(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function x() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var S = 1024, C = 2048, w = 4096, T = 8192, ee = 16384, te = 32768, ne = 1 << 25, re = 65536, ie = 1 << 19, ae = 1 << 20, oe = 1 << 25, se = 65536, ce = 1 << 21, le = 1 << 22, ue = 1 << 23, de = Symbol("$state"), fe = Symbol("legacy props"), pe = Symbol(""), me = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), he = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function ge(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function _e() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function ve(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function ye(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function be() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function xe(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Se() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Ce() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function we(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Te() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Ee() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function De() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Oe() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function ke() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Ae(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function je() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var E = !1;
function Me(e) {
	E = e;
}
var D;
function O(e) {
	if (e === null) throw Ae(), r;
	return D = e;
}
function Ne() {
	return O(/* @__PURE__ */ tn(D));
}
function k(e) {
	if (E) {
		if (/* @__PURE__ */ tn(D) !== null) throw Ae(), r;
		D = e;
	}
}
function Pe(e = 1) {
	if (E) {
		for (var t = e, n = D; t--;) n = /* @__PURE__ */ tn(n);
		D = n;
	}
}
function Fe(e = !0) {
	for (var t = 0, n = D;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ tn(n);
		e && n.remove(), n = i;
	}
}
function Ie(e) {
	if (!e || e.nodeType !== 8) throw Ae(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Le(e) {
	return e === this.v;
}
function Re(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function ze(e) {
	return !Re(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var A = null;
function Be(e) {
	A = e;
}
function Ve(e, n = !1, r) {
	A = {
		p: A,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: W,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function He(e) {
	var t = A, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) vn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, A = t.p, e ?? {};
}
function Ue() {
	return !t || A !== null && A.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var We = [];
function Ge() {
	var e = We;
	We = [], b(e);
}
function Ke(e) {
	if (We.length === 0 && !ot) {
		var t = We;
		queueMicrotask(() => {
			t === We && Ge();
		});
	}
	We.push(e);
}
function qe() {
	for (; We.length > 0;) Ge();
}
function Je(e) {
	var t = W;
	if (t === null) return V.f |= ue, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Ye(e, t);
}
function Ye(e, t) {
	for (; t !== null;) {
		if (t.f & 128) {
			if (!(t.f & 32768)) throw e;
			try {
				t.b.error(e);
				return;
			} catch (t) {
				e = t;
			}
		}
		t = t.parent;
	}
	throw e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var Xe = ~(C | w | S);
function j(e, t) {
	e.f = e.f & Xe | t;
}
function Ze(e) {
	e.f & 512 || e.deps === null ? j(e, S) : j(e, w);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function Qe(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= se, Qe(t.deps));
}
function $e(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), Qe(e.deps), j(e, S);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var et = !1, tt = !1;
function nt(e) {
	var t = tt;
	try {
		return tt = !1, [e(), tt];
	} finally {
		tt = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var rt = /* @__PURE__ */ new Set(), M = null, it = null, N = null, at = null, ot = !1, st = !1, ct = null, lt = null, ut = 0, dt = 1, ft = class t {
	id = dt++;
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#e = /* @__PURE__ */ new Set();
	#t = /* @__PURE__ */ new Set();
	#n = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Map();
	#i = /* @__PURE__ */ new Map();
	#a = null;
	#o = [];
	#s = [];
	#c = /* @__PURE__ */ new Set();
	#l = /* @__PURE__ */ new Set();
	#u = /* @__PURE__ */ new Map();
	#d = /* @__PURE__ */ new Set();
	is_fork = !1;
	#f = !1;
	#p = /* @__PURE__ */ new Set();
	#m() {
		return this.is_fork || this.#i.size > 0;
	}
	#h() {
		for (let n of this.#p) for (let r of n.#i.keys()) {
			for (var e = !1, t = r; t.parent !== null;) {
				if (this.#u.has(t)) {
					e = !0;
					break;
				}
				t = t.parent;
			}
			if (!e) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#u.has(e) || this.#u.set(e, {
			d: [],
			m: []
		}), this.#d.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#u.get(e);
		if (n) {
			this.#u.delete(e);
			for (var r of n.d) j(r, C), t(r);
			for (r of n.m) j(r, w), t(r);
		}
		this.#d.add(e);
	}
	#g() {
		if (ut++ > 1e3 && (rt.delete(this), mt()), !this.#m()) {
			for (let e of this.#c) this.#l.delete(e), j(e, C), this.schedule(e);
			for (let e of this.#l) j(e, w), this.schedule(e);
		}
		let n = this.#o;
		this.#o = [], this.apply();
		var r = ct = [], i = [], a = lt = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw xt(e), t;
		}
		if (M = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (ct = null, lt = null, this.#m() || this.#h()) {
			this.#v(i), this.#v(r);
			for (let [e, t] of this.#u) bt(e, t);
		} else {
			this.#r.size === 0 && rt.delete(this), this.#c.clear(), this.#l.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), it = this, gt(i), gt(r), it = null, this.#a?.resolve();
		}
		var s = M;
		if (this.#o.length > 0) {
			let e = s ??= this;
			e.#o.push(...this.#o.filter((t) => !e.#o.includes(t)));
		}
		s !== null && (rt.add(s), s.#g()), e && !rt.has(this) && this.#y();
	}
	#_(t, n, r) {
		t.f ^= S;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#u.has(i)) && i.fn !== null) {
				o ? i.f ^= S : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Jn(i) && (a & 16 && this.#l.add(i), $n(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#v(e) {
		for (var t = 0; t < e.length; t += 1) $e(e[t], this.#c, this.#l);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), N?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		M = this;
	}
	deactivate() {
		M = null, N = null;
	}
	flush() {
		try {
			st = !0, M = this, this.#g();
		} finally {
			ut = 0, at = null, ct = null, lt = null, st = !1, M = null, N = null, zt.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear(), this.#n.clear(), rt.delete(this);
	}
	register_created_effect(e) {
		this.#s.push(e);
	}
	#y() {
		for (let l of rt) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			var r = [...l.current.keys()].filter((e) => !this.current.has(e));
			if (r.length === 0) e && l.discard();
			else if (t.length > 0) {
				if (e) for (let e of this.#d) l.unskip_effect(e, (e) => {
					e.f & 4194320 ? l.schedule(e) : l.#v([e]);
				});
				l.activate();
				var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
				for (var o of t) _t(o, r, i, a);
				a = /* @__PURE__ */ new Map();
				var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e : !0);
				for (let e of this.#s) !(e.f & 155648) && vt(e, s, a) && (e.f & 4194320 ? (j(e, C), l.schedule(e)) : l.#c.add(e));
				if (l.#o.length > 0) {
					l.apply();
					for (var c of l.#o) l.#_(c, [], []);
					l.#o = [];
				}
				l.deactivate();
			}
		}
		for (let e of rt) e.#p.has(this) && (e.#p.delete(this), e.#p.size === 0 && !e.#m() && (e.activate(), e.#g()));
	}
	increment(e, t) {
		let n = this.#r.get(t) ?? 0;
		if (this.#r.set(t, n + 1), e) {
			let e = this.#i.get(t) ?? 0;
			this.#i.set(t, e + 1);
		}
	}
	decrement(e, t, n) {
		let r = this.#r.get(t) ?? 0;
		if (r === 1 ? this.#r.delete(t) : this.#r.set(t, r - 1), e) {
			let e = this.#i.get(t) ?? 0;
			e === 1 ? this.#i.delete(t) : this.#i.set(t, e - 1);
		}
		this.#f || n || (this.#f = !0, Ke(() => {
			this.#f = !1, this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#c.add(t);
		for (let e of t) this.#l.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#e.add(e);
	}
	ondiscard(e) {
		this.#t.add(e);
	}
	on_fork_commit(e) {
		this.#n.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#n) e(this);
		this.#n.clear();
	}
	settled() {
		return (this.#a ??= x()).promise;
	}
	static ensure() {
		if (M === null) {
			let e = M = new t();
			st || (rt.add(M), ot || Ke(() => {
				M === e && e.flush();
			}));
		}
		return M;
	}
	apply() {
		if (!e || !this.is_fork && rt.size === 1) {
			N = null;
			return;
		}
		N = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) N.set(e, t);
		for (let e of rt) if (!(e === this || e.is_fork)) {
			var t = !1, n = !1;
			if (e.id < this.id) for (let [r, [, i]] of e.current) i || (t ||= this.current.has(r), n ||= !this.current.has(r));
			if (t && n) this.#p.add(e);
			else for (let [t, n] of e.previous) N.has(t) || N.set(t, n);
		}
	}
	schedule(t) {
		if (at = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (ct !== null && n === W && (e || (V === null || !(V.f & 2)) && !et)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= S;
			}
		}
		this.#o.push(n);
	}
};
function pt(e) {
	var t = ot;
	ot = !0;
	try {
		var n;
		for (e && (M !== null && !M.is_fork && M.flush(), n = e());;) {
			if (qe(), M === null) return n;
			M.flush();
		}
	} finally {
		ot = t;
	}
}
function mt() {
	try {
		Se();
	} catch (e) {
		Ye(e, at);
	}
}
var ht = null;
function gt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Jn(r) && (ht = /* @__PURE__ */ new Set(), $n(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && An(r), ht?.size > 0)) {
				zt.clear();
				for (let e of ht) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) ht.has(n) && (ht.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || $n(n);
					}
				}
				ht.clear();
			}
		}
		ht = null;
	}
}
function _t(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? _t(i, t, n, r) : e & 4194320 && !(e & 2048) && vt(i, t, r) && (j(i, C), yt(i));
	}
}
function vt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && vt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function yt(e) {
	M.schedule(e);
}
function bt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), j(e, S);
		for (var n = e.first; n !== null;) bt(n, t), n = n.next;
	}
}
function xt(e) {
	j(e, S);
	for (var t = e.first; t !== null;) xt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function St(e) {
	let t = 0, n = Vt(0), r;
	return () => {
		hn() && (Y(n), Cn(() => (t === 0 && (r = X(() => e(() => Kt(n)))), t += 1, () => {
			Ke(() => {
				--t, t === 0 && (r?.(), r = void 0, Kt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var Ct = re | ie;
function wt(e, t, n, r) {
	new Tt(e, t, n, r);
}
var Tt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = E ? D : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = St(() => (this.#m = Vt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Tn(() => {
			if (E) {
				let e = this.#t;
				Ne();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, Ct), E && (this.#e = D);
	}
	#g() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = z(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), Ke(() => {
			var e = this.#c = document.createDocumentFragment(), t = I();
			e.append(t), this.#a = this.#x(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, jn(this.#o, () => {
				this.#o = null;
			}), this.#b(M));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Fn(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#b(M);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		$e(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = W, n = V, r = A;
		Bn(this.#i), U(this.#i), Be(this.#i.ctx);
		try {
			return ft.ensure(), e();
		} catch (e) {
			return Je(e), null;
		} finally {
			Bn(t), U(n), Be(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && jn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Ke(() => {
			this.#d = !1, this.#m && Wt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Y(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		M?.is_fork ? (this.#a && M.skip_effect(this.#a), this.#o && M.skip_effect(this.#o), this.#s && M.skip_effect(this.#s), M.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), E && (O(this.#t), Pe(), O(Fe()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				je();
				return;
			}
			r = !0, i && Oe(), this.#s !== null && jn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				Ye(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return z(() => {
						var t = W;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return Ye(e, this.#i.parent), null;
				}
			}));
		};
		Ke(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				Ye(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => Ye(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function Et(e, t, n, r) {
	let i = Ue() ? At : Mt;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = W, s = Dt(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		s();
		try {
			r(e);
		} catch (e) {
			o.f & 16384 || Ye(e, o);
		}
		Ot();
	}
	if (n.length === 0) {
		c.then(() => l(t.map(i)));
		return;
	}
	var u = kt();
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ jt(e))).then((e) => l([...t.map(i), ...e])).catch((e) => Ye(e, o)).finally(() => u());
	}
	c ? c.then(() => {
		s(), d(), Ot();
	}) : d();
}
function Dt() {
	var e = W, t = V, n = A, r = M;
	return function(i = !0) {
		Bn(e), U(t), Be(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Ot(e = !0) {
	Bn(null), U(null), Be(null), e && M?.deactivate();
}
function kt() {
	var e = W, t = e.b, n = M, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), (i = !1) => {
		t.update_pending_count(-1, n), n.decrement(r, e, i);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function At(e) {
	var t = 2 | C;
	return W !== null && (W.f |= ie), {
		ctx: A,
		deps: null,
		effects: null,
		equals: Le,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: W,
		ac: null
	};
}
/* @__NO_SIDE_EFFECTS__ */
function jt(e, t, n) {
	let r = W;
	r === null && _e();
	var a = void 0, o = Vt(i), s = !V, c = /* @__PURE__ */ new Map();
	return Sn(() => {
		var t = W, n = x();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, n.reject).finally(Ot);
		} catch (e) {
			n.reject(e), Ot();
		}
		var i = M;
		if (s) {
			if (t.f & 32768) var l = kt();
			if (r.b.is_rendered()) c.get(i)?.reject(me), c.delete(i);
			else {
				for (let e of c.values()) e.reject(me);
				c.clear();
			}
			c.set(i, n);
		}
		let u = (e, n = void 0) => {
			if (l && l(n === me), !(n === me || t.f & 16384)) {
				if (i.activate(), n) o.f |= ue, Wt(o, n);
				else {
					o.f & 8388608 && (o.f ^= ue), Wt(o, e);
					for (let [e, t] of c) {
						if (c.delete(e), e === i) break;
						t.reject(me);
					}
				}
				i.deactivate();
			}
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), gn(() => {
		for (let e of c.values()) e.reject(me);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Mt(e) {
	let t = /* @__PURE__ */ At(e);
	return t.equals = ze, t;
}
function Nt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function Pt(e) {
	var t, n = W, r = e.parent;
	if (!Rn && r !== null && r.f & 24576) return ke(), e.v;
	Bn(r);
	try {
		e.f &= ~se, Nt(e), t = Xn(e);
	} finally {
		Bn(n);
	}
	return t;
}
function Ft(e) {
	var t = Pt(e);
	if (!e.equals(t) && (e.wv = qn(), (!M?.is_fork || e.deps === null) && (M === null ? e.v = t : M.capture(e, t, !0), e.deps === null))) {
		j(e, S);
		return;
	}
	Rn || (N === null ? Ze(e) : (hn() || M?.is_fork) && N.set(e, t));
}
function It(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(me), t.teardown = v, t.ac = null, Qn(t, 0), Dn(t));
}
function Lt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && $n(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Rt = /* @__PURE__ */ new Set(), zt = /* @__PURE__ */ new Map(), Bt = !1;
function Vt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Le,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Ht(e, t) {
	let n = Vt(e, t);
	return Vn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function P(e, n = !1, r = !0) {
	let i = Vt(e);
	return n || (i.equals = ze), t && r && A !== null && A.l !== null && (A.l.s ??= []).push(i), i;
}
function Ut(e, t) {
	return F(e, X(() => Y(e))), t;
}
function F(e, t, n = !1) {
	return V !== null && (!H || V.f & 131072) && Ue() && V.f & 4325394 && (G === null || !c.call(G, e)) && De(), Wt(e, n ? Jt(t) : t, lt);
}
function Wt(e, t, n = null) {
	if (!e.equals(t)) {
		zt.set(e, Rn ? t : e.v);
		var r = ft.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Pt(t), N === null && Ze(t);
		}
		e.wv = qn(), qt(e, C, n), Ue() && W !== null && W.f & 1024 && !(W.f & 96) && (J === null ? Hn([e]) : J.push(e)), !r.is_fork && Rt.size > 0 && !Bt && Gt();
	}
	return t;
}
function Gt() {
	Bt = !1;
	for (let e of Rt) e.f & 1024 && j(e, w), Jn(e) && $n(e);
	Rt.clear();
}
function Kt(e) {
	F(e, e.v + 1);
}
function qt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ue(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === W)) {
			var l = (c & C) === 0;
			if (l && j(s, t), c & 2) {
				var u = s;
				N?.delete(u), c & 65536 || (c & 512 && (W === null || !(W.f & 2097152)) && (s.f |= se), qt(u, w, n));
			} else if (l) {
				var d = s;
				c & 16 && ht !== null && ht.add(d), n === null ? yt(d) : n.push(d);
			}
		}
	}
}
function Jt(e) {
	if (typeof e != "object" || !e || de in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Ht(0), s = null, c = Gn, l = (e) => {
		if (Gn === c) return e();
		var t = V, n = Gn;
		U(null), Kn(c);
		var r = e();
		return U(t), Kn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Ht(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Te();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Ht(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Ht(i, s));
					n.set(t, e), Kt(a);
				}
			} else F(r, i), Kt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === de) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ Ht(Jt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Y(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Y(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === de) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || W !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Ht(a ? Jt(e[t]) : i, s)), n.set(t, r)), Y(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Ht(i, s)), n.set(p + "", m)) : F(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Ht(void 0, s)), F(u, Jt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Jt(o));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && F(_, v + 1);
				}
				Kt(a);
			}
			return !0;
		},
		ownKeys(e) {
			Y(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Ee();
		}
	});
}
var Yt, Xt, Zt, Qt;
function $t() {
	if (Yt === void 0) {
		Yt = window, Xt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Zt = f(t, "firstChild").get, Qt = f(t, "nextSibling").get, _(e) && (e.__click = void 0, e.__className = void 0, e.__attributes = null, e.__style = void 0, e.__e = void 0), _(n) && (n.__t = void 0);
	}
}
function I(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function en(e) {
	return Zt.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function tn(e) {
	return Qt.call(e);
}
function L(e, t) {
	if (!E) return /* @__PURE__ */ en(e);
	var n = /* @__PURE__ */ en(D);
	if (n === null) n = D.appendChild(I());
	else if (t && n.nodeType !== 3) {
		var r = I();
		return n?.before(r), O(r), r;
	}
	return t && sn(n), O(n), n;
}
function nn(e, t = !1) {
	if (!E) {
		var n = /* @__PURE__ */ en(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ tn(n) : n;
	}
	if (t) {
		if (D?.nodeType !== 3) {
			var r = I();
			return D?.before(r), O(r), r;
		}
		sn(D);
	}
	return D;
}
function R(e, t = 1, n = !1) {
	let r = E ? D : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ tn(r);
	if (!E) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = I();
			return r === null ? i?.after(a) : r.before(a), O(a), a;
		}
		sn(r);
	}
	return O(r), r;
}
function rn(e) {
	e.textContent = "";
}
function an() {
	return !e || ht !== null ? !1 : (W.f & te) !== 0;
}
function on(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function sn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var cn = !1;
function ln() {
	cn || (cn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t.__on_r?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function un(e) {
	var t = V, n = W;
	U(null), Bn(null);
	try {
		return e();
	} finally {
		U(t), Bn(n);
	}
}
function dn(e, t, n, r = n) {
	e.addEventListener(t, () => un(n));
	let i = e.__on_r;
	i ? e.__on_r = () => {
		i(), r(!0);
	} : e.__on_r = () => r(!0), ln();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function fn(e) {
	W === null && (V === null && xe(e), be()), Rn && ye(e);
}
function pn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function mn(e, t) {
	var n = W;
	n !== null && n.f & 8192 && (e |= T);
	var r = {
		ctx: A,
		deps: null,
		nodes: null,
		f: e | C | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	M?.register_created_effect(r);
	var i = r;
	if (e & 4) ct === null ? ft.ensure().schedule(r) : ct.push(r);
	else if (t !== null) {
		try {
			$n(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= re));
	}
	if (i !== null && (i.parent = n, n !== null && pn(i, n), V !== null && V.f & 2 && !(e & 64))) {
		var a = V;
		(a.effects ??= []).push(i);
	}
	return r;
}
function hn() {
	return V !== null && !H;
}
function gn(e) {
	let t = mn(8, null);
	return j(t, S), t.teardown = e, t;
}
function _n(e) {
	fn("$effect");
	var t = W.f;
	if (!V && t & 32 && !(t & 32768)) {
		var n = A;
		(n.e ??= []).push(e);
	} else return vn(e);
}
function vn(e) {
	return mn(4 | ae, e);
}
function yn(e) {
	return fn("$effect.pre"), mn(8 | ae, e);
}
function bn(e) {
	ft.ensure();
	let t = mn(64 | ie, e);
	return () => {
		B(t);
	};
}
function xn(e) {
	ft.ensure();
	let t = mn(64 | ie, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? jn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function Sn(e) {
	return mn(le | ie, e);
}
function Cn(e, t = 0) {
	return mn(8 | t, e);
}
function wn(e, t = [], n = [], r = []) {
	Et(r, t, n, (t) => {
		mn(8, () => e(...t.map(Y)));
	});
}
function Tn(e, t = 0) {
	return mn(16 | t, e);
}
function z(e) {
	return mn(32 | ie, e);
}
function En(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Rn, n = V;
		zn(!0), U(null);
		try {
			t.call(null);
		} finally {
			zn(e), U(n);
		}
	}
}
function Dn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && un(() => {
			e.abort(me);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function On(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (kn(e.nodes.start, e.nodes.end), n = !0), j(e, ne), Dn(e, t && !n), Qn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	En(e), e.f ^= ne, e.f |= ee;
	var i = e.parent;
	i !== null && i.first !== null && An(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function kn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ tn(e);
		e.remove(), e = n;
	}
}
function An(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function jn(e, t, n = !0) {
	var r = [];
	Mn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Mn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= T;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Mn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Nn(e) {
	Pn(e, !0);
}
function Pn(e, t) {
	if (e.f & 8192) {
		e.f ^= T, e.f & 1024 || (j(e, C), ft.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Pn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Fn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ tn(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var In = null, Ln = !1, Rn = !1;
function zn(e) {
	Rn = e;
}
var V = null, H = !1;
function U(e) {
	V = e;
}
var W = null;
function Bn(e) {
	W = e;
}
var G = null;
function Vn(t) {
	V !== null && (!e || V.f & 2) && (G === null ? G = [t] : G.push(t));
}
var K = null, q = 0, J = null;
function Hn(e) {
	J = e;
}
var Un = 1, Wn = 0, Gn = Wn;
function Kn(e) {
	Gn = e;
}
function qn() {
	return ++Un;
}
function Jn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~se), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Jn(a) && Ft(a), a.wv > e.wv) return !0;
		}
		t & 512 && N === null && j(e, S);
	}
	return !1;
}
function Yn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && G !== null && c.call(G, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Yn(o, n, !1) : n === o && (r ? j(o, C) : o.f & 1024 && j(o, w), yt(o));
	}
}
function Xn(e) {
	var t = K, n = q, r = J, i = V, a = G, o = A, s = H, c = Gn, l = e.f;
	K = null, q = 0, J = null, V = l & 96 ? null : e, G = null, Be(e.ctx), H = !1, Gn = ++Wn, e.ac !== null && (un(() => {
		e.ac.abort(me);
	}), e.ac = null);
	try {
		e.f |= ce;
		var u = e.fn, d = u();
		e.f |= te;
		var f = e.deps, p = M?.is_fork;
		if (K !== null) {
			var m;
			if (p || Qn(e, q), f !== null && q > 0) for (f.length = q + K.length, m = 0; m < K.length; m++) f[q + m] = K[m];
			else e.deps = f = K;
			if (hn() && e.f & 512) for (m = q; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && q < f.length && (Qn(e, q), f.length = q);
		if (Ue() && J !== null && !H && f !== null && !(e.f & 6146)) for (m = 0; m < J.length; m++) Yn(J[m], e);
		if (i !== null && i !== e) {
			if (Wn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Wn;
			if (t !== null) for (let e of t) e.rv = Wn;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= ue), d;
	} catch (e) {
		return Je(e);
	} finally {
		e.f ^= ce, K = t, q = n, J = r, V = i, G = a, Be(o), H = s, Gn = c;
	}
}
function Zn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (K === null || !c.call(K, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~se), o.v !== i && Ze(o), It(o), Qn(o, 0);
	}
}
function Qn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Zn(e, n[r]);
}
function $n(e) {
	var t = e.f;
	if (!(t & 16384)) {
		j(e, S);
		var n = W, r = Ln;
		W = e, Ln = !0;
		try {
			t & 16777232 ? On(e) : Dn(e), En(e);
			var i = Xn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Un;
		} finally {
			Ln = r, W = n;
		}
	}
}
async function er() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), pt();
}
function Y(e) {
	var t = (e.f & 2) != 0;
	if (In?.add(e), V !== null && !H && !(W !== null && W.f & 16384) && (G === null || !c.call(G, e))) {
		var n = V.deps;
		if (V.f & 2097152) e.rv < Wn && (e.rv = Wn, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			(V.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [V] : c.call(r, V) || r.push(V);
		}
	}
	if (Rn && zt.has(e)) return zt.get(e);
	if (t) {
		var i = e;
		if (Rn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || nr(i)) && (a = Pt(i)), zt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !H && V !== null && (Ln || (V.f & 512) != 0), s = (i.f & te) === 0;
		Jn(i) && (o && (i.f |= 512), Ft(i)), o && !s && (Lt(i), tr(i));
	}
	if (N?.has(e)) return N.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function tr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Lt(t), tr(t));
}
function nr(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (zt.has(t) || t.f & 2 && nr(t)) return !0;
	return !1;
}
function X(e) {
	var t = H;
	try {
		return H = !0, e();
	} finally {
		H = t;
	}
}
function rr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (de in e) ir(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && de in n && ir(n);
		}
	}
}
function ir(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			ir(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var ar = Symbol("events"), or = /* @__PURE__ */ new Set(), sr = /* @__PURE__ */ new Set();
function cr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || ur.call(t, e), !e.cancelBubble) return un(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Ke(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = cr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && gn(() => {
		t.removeEventListener(e, o, a);
	});
}
var lr = null;
function ur(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	lr = e;
	var o = 0, s = lr === e && e[ar];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[ar] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = V, f = W;
		U(null), Bn(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[ar]?.[r];
					g != null && (!a.disabled || e.target === a) && g.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble || h === t || h === null) break;
				a = h;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[ar] = t, delete e.currentTarget, U(u), Bn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var dr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function fr(e) {
	return dr?.createHTML(e) ?? e;
}
function pr(e) {
	var t = on("template");
	return t.innerHTML = fr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function mr(e, t) {
	var n = W;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (E) return mr(D, null), D;
		i === void 0 && (i = pr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ en(i)));
		var t = r || Xt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ en(t), s = t.lastChild;
			mr(o, s);
		} else mr(t, t);
		return t;
	};
}
function $(e, t) {
	if (E) {
		var n = W;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = D), Ne();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var hr = ["touchstart", "touchmove"];
function gr(e) {
	return hr.includes(e);
}
function _r(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e.__t ??= e.nodeValue) && (e.__t = n, e.nodeValue = `${n}`);
}
function vr(e, t) {
	return xr(e, t);
}
function yr(e, t) {
	$t(), t.intro = t.intro ?? !1;
	let n = t.target, i = E, a = D;
	try {
		for (var o = /* @__PURE__ */ en(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ tn(o);
		if (!o) throw r;
		Me(!0), O(o);
		let i = xr(e, {
			...t,
			anchor: o
		});
		return Me(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && Ce(), $t(), rn(n), Me(!1), vr(e, t);
	} finally {
		Me(i), O(a);
	}
}
var br = /* @__PURE__ */ new Map();
function xr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	$t();
	var u = void 0, d = xn(() => {
		var s = n ?? t.appendChild(I());
		wt(s, { pending: () => {} }, (t) => {
			Ve({});
			var n = A;
			if (o && (n.c = o), a && (i.$$events = a), E && mr(t, null), u = e(t, i) || {}, E && (W.nodes.end = D, D === null || D.nodeType !== 8 || D.data !== "]")) throw Ae(), r;
			He();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = gr(r);
					for (let e of [t, document]) {
						var a = br.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), br.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, ur, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(or)), sr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = br.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, ur), r.delete(e), r.size === 0 && br.delete(n)) : r.set(e, i);
			}
			sr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return Sr.set(u, d), u;
}
var Sr = /* @__PURE__ */ new WeakMap();
function Cr(e, t) {
	let n = Sr.get(e);
	return n ? (Sr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var wr = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Nn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (B(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Fn(r, t), t.append(I()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), jn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = M, r = an();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = I();
			i.append(a), this.#n.set(e, {
				effect: z(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, z(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else E && (this.anchor = D), this.#a(n);
	}
};
function Tr(e) {
	A === null && ge("onMount"), t && A.l !== null ? Er(A).m.push(e) : _n(() => {
		let t = X(e);
		if (typeof t == "function") return t;
	});
}
function Er(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Dr(e, t, n = !1) {
	var r;
	E && (r = D, Ne());
	var i = new wr(e), a = n ? re : 0;
	function o(e, t) {
		if (E) {
			var n = Ie(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Fe();
				O(a), i.anchor = a, Me(!1), i.ensure(e, t), Me(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Tn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Or(e, t) {
	return t;
}
function kr(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		jn(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Ar(e, l(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null;
		if (c) {
			var u = n, d = u.parentNode;
			rn(d), d.append(u), e.items.clear();
		}
		Ar(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Ar(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= oe, Fn(a, document.createDocumentFragment())) : B(t[i], n);
	}
}
var jr;
function Mr(e, t, n, r, i, a = null) {
	var s = e, c = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = E ? O(/* @__PURE__ */ en(u)) : u.appendChild(I());
	}
	E && Ne();
	var d = null, f = /* @__PURE__ */ Mt(() => {
		var e = n();
		return o(e) ? e : e == null ? [] : l(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Pr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= oe, Ir(d, null, s)) : Nn(d) : jn(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: Tn(() => {
			p = Y(f);
			var e = p.length;
			let o = !1;
			E && Ie(s) === "[!" != (e === 0) && (s = Fe(), O(s), Me(!1), o = !0);
			for (var l = /* @__PURE__ */ new Set(), u = M, v = an(), y = 0; y < e; y += 1) {
				E && D.nodeType === 8 && D.data === "]" && (s = D, o = !0, Me(!1));
				var b = p[y], x = r(b, y), S = h ? null : c.get(x);
				S ? (S.v && Wt(S.v, b), S.i && Wt(S.i, y), v && u.unskip_effect(S.e)) : (S = Fr(c, h ? s : jr ??= I(), b, x, y, i, t, n), h || (S.e.f |= oe), c.set(x, S)), l.add(x);
			}
			if (e === 0 && a && !d && (h ? d = z(() => a(s)) : (d = z(() => a(jr ??= I())), d.f |= oe)), e > l.size && ve("", "", ""), E && e > 0 && O(Fe()), !h) if (m.set(u, l), v) {
				for (let [e, t] of c) l.has(e) || u.skip_effect(t.e);
				u.oncommit(g), u.ondiscard(_);
			} else g(u);
			o && Me(!0), Y(f);
		}),
		flags: t,
		items: c,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, E && (s = D);
}
function Nr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Pr(e, t, n, r, i) {
	var a = (r & 8) != 0, o = t.length, s = e.items, c = Nr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Nn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= oe, _ === c) Ir(_, null, n);
		else {
			var y = d ? d.next : c;
			_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Lr(e, d, _), Lr(e, _, y), Ir(_, y, n), d = _, p = [], m = [], c = Nr(d.next);
			continue;
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Ir(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Lr(e, S.prev, C.next), Lr(e, d, S), Lr(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Ir(_, c, n), Lr(e, _.prev, _.next), Lr(e, _, d === null ? e.effect.first : d.next), Lr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = Nr(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = Nr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Ar(e, l(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && w.push(c), c = Nr(c.next);
		var T = w.length;
		if (T > 0) {
			var ee = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < T; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < T; v += 1) w[v].nodes?.a?.fix();
			}
			kr(e, w, ee);
		}
	}
	a && Ke(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Fr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Vt(n) : /* @__PURE__ */ P(n, !1, !1) : null, l = o & 2 ? Vt(i) : null;
	return {
		v: c,
		i: l,
		e: z(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Ir(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ tn(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Lr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var Rr = [..." 	\n\r\f\xA0\v﻿"];
function zr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Rr.includes(r[o - 1])) && (s === r.length || Rr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Br(e, t, n, r, i, a) {
	var o = e.__className;
	if (E || o !== n || o === void 0) {
		var s = zr(n, r, a);
		(!E || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e.__className = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Vr = Symbol("is custom element"), Hr = Symbol("is html"), Ur = he ? "link" : "LINK";
function Wr(e) {
	if (E) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Gr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Gr(e, "checked", null), e.checked = r;
				}
			}
		};
		e.__on_r = n, Ke(n), ln();
	}
}
function Gr(e, t, n, r) {
	var i = Kr(e);
	E && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Ur) || i[t] !== (i[t] = n) && (t === "loading" && (e[pe] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Jr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Kr(e) {
	return e.__attributes ??= {
		[Vr]: e.nodeName.includes("-"),
		[Hr]: e.namespaceURI === a
	};
}
var qr = /* @__PURE__ */ new Map();
function Jr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = qr.get(t);
	if (n) return n;
	qr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Yr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	dn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Xr(t) ? Zr(a) : a, r(a), M !== null && i.add(M), await er(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (E && t.defaultValue !== t.value || X(n) == null && t.value) && (r(Xr(t) ? Zr(t.value) : t.value), M !== null && i.add(M)), Cn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? it : M;
			if (i.has(a)) return;
		}
		Xr(t) && r === Zr(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Xr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Zr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function Qr(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function $r(e = !1) {
	let t = A, n = t.l.u;
	if (!n) return;
	let r = () => rr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ At(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && yn(() => {
		ei(t, r), b(n.b);
	}), _n(() => {
		let e = X(() => n.m.map(y));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && _n(() => {
		ei(t, r), b(n.a);
	});
}
function ei(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function ti(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of o(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function ni(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = () => (l && (l = !1, c = s ? X(i) : i), c);
	let d;
	if (o) {
		var p = de in e || fe in e;
		d = f(e, n)?.set ?? (p && n in e ? (t) => e[n] = t : void 0);
	}
	var m, h = !1;
	o ? [m, h] = nt(() => e[n]) : m = e[n], m === void 0 && i !== void 0 && (m = u(), d && (a && we(n), d(m)));
	var g = a ? () => {
		var t = e[n];
		return t === void 0 ? u() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return g;
	if (d) {
		var _ = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || _ || h) && d(t ? g() : e), e) : g();
		});
	}
	var v = !1, y = (r & 1 ? At : Mt)(() => (v = !1, g()));
	o && Y(y);
	var b = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(y) : a && o ? Jt(e) : e;
			return F(y, n), v = !0, c !== void 0 && (c = n), e;
		}
		return Rn && v || b.f & 16384 ? y.v : Y(y);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function ri(e) {
	return new ii(e);
}
var ii = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ P(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Y(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === fe ? !0 : (Y(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return F(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? yr : vr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && pt(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			Cr(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, ai;
typeof HTMLElement == "function" && (ai = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = on("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = si(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = oi(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = ri({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = bn(() => {
				Cn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = oi(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = oi(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function oi(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function si(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function ci(e, t, n, r, i, a) {
	let o = class extends ai {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = oi(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region TidalCard.svelte
var li = /* @__PURE__ */ Q("<div class=\"p-5 text-center text-secondary\">Loading...</div>"), ui = /* @__PURE__ */ Q("<div class=\"redirect-uri-group\"><input type=\"text\" placeholder=\"Loading dynamic redirect URI...\" class=\"px-3 py-2 bg-background/50 border border-border rounded-global text-sm text-primary w-full box-border opacity-70 cursor-not-allowed select-all\"/></div> <p class=\"text-xs text-secondary mt-1\" style=\"margin-top: 8px;\">This auto-generated URI must be registered in all of your Tidal Developer Applications.</p>", 1), di = /* @__PURE__ */ Q("<button class=\"px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\">+ Add Account</button>"), fi = /* @__PURE__ */ Q("<span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-[#00e676]/20 text-[#00e676]\">✓ Authenticated</span>"), pi = /* @__PURE__ */ Q("<span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-yellow-500/20 text-yellow-500\">⚠ Not Authenticated</span>"), mi = /* @__PURE__ */ Q("<span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-[#ba6415]/20 text-[#ba6415]\">● Active</span>"), hi = /* @__PURE__ */ Q("<span class=\"status-badge configured\">🔒 Configured</span>"), gi = /* @__PURE__ */ Q("<div class=\"flex justify-between items-center p-3 bg-white/5 border border-white/10 rounded-global\"><div class=\"flex flex-col gap-1\"><div class=\"font-medium text-[14px]\"> </div> <div class=\"flex gap-[6px] flex-wrap\"><!> <!> <!></div></div> <div class=\"flex gap-2 items-center flex-wrap\"><button class=\"bg-transparent text-[#ba6415] px-2 py-1 hover:underline active:scale-95 transition-all duration-200\" title=\"Edit credentials\">⚙️ Edit</button> <button class=\"bg-transparent text-[#ba6415] px-2 py-1 hover:underline active:scale-95 transition-all duration-200\"> </button> <button> </button> <button class=\"px-4 py-2 bg-red-500/20 text-red-500 border-none rounded-global transition-colors hover:bg-red-500/30 active:scale-95\">✕</button></div></div>"), _i = /* @__PURE__ */ Q("<div class=\"p-4 text-center text-secondary text-sm\">No accounts added yet. Click \"Add Account\" to get started.</div>"), vi = /* @__PURE__ */ Q("<div class=\"mb-6\"><div class=\"mb-3\"><h3 class=\"m-0 mb-4 text-base font-semibold\">Global Redirect URI (Auto-generated & Immutable)</h3> <button class=\"px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\"> </button></div> <!></div> <div class=\"mb-6\"><div class=\"mb-3\"><h3 class=\"m-0 mb-4 text-base font-semibold\"> </h3> <p class=\"text-xs text-secondary mt-1\">Tidal requires per-account Client ID and Secret.</p> <!></div> <div class=\"flex flex-col gap-2\"></div></div>", 1), yi = /* @__PURE__ */ Q("<div class=\"fixed inset-0 bg-black/60 flex items-center justify-center z-[1000]\"><div class=\"bg-[#1e1e2e] rounded-[10px] p-0 min-w-[420px] max-w-[90vw] border border-white/15\"><div class=\"flex justify-between items-center px-5 py-4 border-b border-white/10\"><h3 class=\"m-0 mb-4 text-base font-semibold\"> </h3> <button class=\"bg-transparent border-none text-[18px] cursor-pointer text-secondary p-0 leading-none active:scale-95 transition-all duration-200\">✕</button></div> <div class=\"p-5 flex flex-col gap-[14px]\"><label class=\"flex flex-col gap-[6px]\"><span class=\"text-[13px] font-medium text-primary\">Account Name</span> <input type=\"text\" placeholder=\"My Tidal Account\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent\"/></label> <label class=\"flex flex-col gap-[6px]\"><span class=\"text-[13px] font-medium text-primary\">Client ID</span> <input type=\"text\" placeholder=\"Enter Tidal Client ID\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent\"/></label> <label class=\"flex flex-col gap-[6px]\"><span class=\"text-[13px] font-medium text-primary\">Client Secret</span> <div class=\"relative flex items-center\"><input placeholder=\"Enter Tidal Client Secret\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent\"/> <button type=\"button\" class=\"absolute right-2 bg-transparent border-none cursor-pointer text-lg p-1 opacity-60 hover:opacity-100 transition-opacity active:scale-95\"> </button></div></label> <p class=\"text-[12px] text-secondary m-0\">Each Tidal account requires its own Client ID and Client Secret from the Tidal Developer Portal.</p></div> <div class=\"flex justify-end gap-[10px] px-5 py-4 border-t border-white/10\"><button class=\"px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\">Cancel</button> <button class=\"px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\"> </button></div></div></div>"), bi = /* @__PURE__ */ Q("<section class=\"p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global mb-4\"><div class=\"flex justify-between items-center mb-5 pb-3 border-b border-glass-border\"><div class=\"flex items-center gap-3\"><h2 class=\"m-0 text-xl font-semibold\">Tidal</h2> <span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-[#ba6415]/20 text-[#ba6415]\">Streaming Service</span></div></div> <!></section> <!>", 1);
function xi(e, t) {
	Ve(t, !1);
	let n = ni(t, "apiBase", 12, ""), r = /* @__PURE__ */ P([]), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P(!1), o = /* @__PURE__ */ P(!0), s = /* @__PURE__ */ P(!1), c = /* @__PURE__ */ P("add"), l = /* @__PURE__ */ P({
		id: null,
		account_name: "",
		client_id: "",
		client_secret: ""
	}), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1);
	Tr(async () => {
		await f(), F(a, !!Y(i)), F(o, !1);
	});
	async function f() {
		try {
			let e = await fetch(`${n()}/accounts/tidal`);
			e.data && (F(r, e.data.accounts || []), F(i, e.data.redirect_uri || ""), F(a, !!Y(i)));
		} catch (e) {
			console.error("Failed to load Tidal accounts:", e), console.error("Failed to load Tidal accounts");
		}
	}
	function p() {
		F(c, "add"), F(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		}), F(u, !0), F(d, !1), F(s, !0);
	}
	async function m(e) {
		F(c, "edit");
		try {
			let t = await fetch(`${n()}/accounts/tidal/${e.id}`);
			t.data?.account && (F(l, {
				id: t.data.account.id,
				account_name: t.data.account.account_name,
				client_id: t.data.account.client_id || "",
				client_secret: t.data.account.client_secret || ""
			}), F(u, !1), F(d, !1), F(s, !0));
		} catch (e) {
			console.error("Failed to load account credentials:", e), console.error("Failed to load account");
		}
	}
	function h() {
		F(s, !1), F(u, !1), F(d, !1), F(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		});
	}
	async function g() {
		if (!Y(l).account_name.trim() || !Y(l).client_id.trim()) {
			console.error("Account name and Client ID are required");
			return;
		}
		if (!Y(l).client_secret.trim()) {
			console.error("Client Secret is required");
			return;
		}
		if (Y(c) === "add" && Y(r).length >= 25) {
			console.error("Maximum 25 accounts allowed");
			return;
		}
		try {
			let e = {
				account_name: Y(l).account_name,
				client_id: Y(l).client_id,
				client_secret: Y(l).client_secret
			};
			Y(c) === "add" ? (await fetch(`${n()}/accounts/tidal`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), console.log("Account added")) : (await fetch(`${n()}/accounts/tidal/${Y(l).id}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), console.log("Account updated")), h(), await f();
		} catch (e) {
			console.error("Failed to save account:", e), console.error("Failed to save account");
		}
	}
	async function _(e, t) {
		try {
			await fetch(`${n()}/accounts/tidal/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), console.log(t ? "Account deactivated" : "Account activated"), await f();
		} catch (e) {
			console.error("Failed to toggle account:", e), console.error("Failed to update account");
		}
	}
	async function v(e, t) {
		if (confirm(`Delete account "${t}"? This will also delete its credentials.`)) try {
			await fetch(`${n()}/accounts/tidal/${e}`, { method: "DELETE" }), console.log("Account deleted"), await f();
		} catch (e) {
			console.error("Failed to delete account:", e), console.error("Failed to delete account");
		}
	}
	async function y(e) {
		try {
			let t = (await fetch(`${n()}/tidal/auth?account_id=${e}`)).data?.auth_url;
			t ? window.location.href = t : console.error("Failed to get Tidal auth URL");
		} catch (e) {
			console.error("Failed to start OAuth:", e);
			let t = e?.response?.data?.error || "Failed to start OAuth";
			console.error(t);
		}
	}
	var b = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), pt();
		}
	};
	$r();
	var x = bi(), S = nn(x), C = R(L(S), 2), w = (e) => {
		$(e, li());
	}, T = (e) => {
		var t = vi(), n = nn(t), o = L(n), s = R(L(o), 2), c = L(s, !0);
		k(s), k(o);
		var l = R(o, 2), u = (e) => {
			var t = ui(), n = nn(t), r = L(n);
			Wr(r), r.readOnly = !0, r.disabled = !0, k(n), Pe(2), Yr(r, () => Y(i), (e) => F(i, e)), $(e, t);
		};
		Dr(l, (e) => {
			Y(a) || e(u);
		}), k(n);
		var d = R(n, 2), f = L(d), h = L(f), g = L(h);
		k(h);
		var b = R(h, 4), x = (e) => {
			var t = di();
			Z("click", t, p), $(e, t);
		};
		Dr(b, (e) => {
			Y(r), X(() => Y(r).length < 25) && e(x);
		}), k(f);
		var S = R(f, 2);
		Mr(S, 5, () => Y(r), Or, (e, t) => {
			var n = gi(), r = L(n), i = L(r), a = L(i, !0);
			k(i);
			var o = R(i, 2), s = L(o), c = (e) => {
				$(e, fi());
			}, l = (e) => {
				$(e, pi());
			};
			Dr(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = R(s, 2), d = (e) => {
				$(e, mi());
			};
			Dr(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			});
			var f = R(u, 2), p = (e) => {
				$(e, hi());
			};
			Dr(f, (e) => {
				Y(t), X(() => Y(t).client_secret_configured) && e(p);
			}), k(o), k(r);
			var h = R(r, 2), g = L(h), b = R(g, 2), x = L(b, !0);
			k(b);
			var S = R(b, 2);
			let C;
			var w = L(S, !0);
			k(S);
			var T = R(S, 2);
			k(h), k(n), wn(() => {
				_r(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), _r(x, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), C = Br(S, 1, "px-4 py-2 bg-white/10 text-primary border-none rounded-global transition-colors hover:bg-white/15 active:scale-95", null, C, { active: Y(t).is_active }), Gr(S, "title", (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate"))), _r(w, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", g, () => m(Y(t))), Z("click", b, () => y(Y(t).id)), Z("click", S, () => _(Y(t).id, Y(t).is_active)), Z("click", T, () => v(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, _i());
		}), k(S), k(d), wn(() => {
			_r(c, Y(a) ? "Expand" : "Collapse"), _r(g, `Accounts (${(Y(r), X(() => Y(r).length)) ?? ""}/25)`);
		}), Z("click", s, () => F(a, !Y(a))), $(e, t);
	};
	Dr(C, (e) => {
		Y(o) ? e(w) : e(T, -1);
	}), k(S);
	var ee = R(S, 2), te = (e) => {
		var n = yi(), r = L(n), i = L(r), a = L(i), o = L(a, !0);
		k(a);
		var s = R(a, 2);
		k(i);
		var f = R(i, 2), p = L(f), m = R(L(p), 2);
		Wr(m), k(p);
		var _ = R(p, 2), v = R(L(_), 2);
		Wr(v), k(_);
		var y = R(_, 2), b = R(L(y), 2), x = L(b);
		Wr(x);
		var S = R(x, 2), C = L(S, !0);
		k(S), k(b), k(y), Pe(2), k(f);
		var w = R(f, 2), T = L(w), ee = R(T, 2), te = L(ee, !0);
		k(ee), k(w), k(r), k(n), wn(() => {
			_r(o, Y(c) === "add" ? "Add Tidal Account" : "Edit Tidal Account"), Gr(x, "type", Y(d) ? "text" : "password"), Gr(S, "title", Y(d) ? "Hide" : "Show"), _r(C, Y(d) ? "👁️" : "👁️‍🗨️"), _r(te, Y(c) === "add" ? "Add Account" : "Save Changes");
		}), Z("click", s, h), Yr(m, () => Y(l).account_name, (e) => Ut(l, Y(l).account_name = e)), Yr(v, () => Y(l).client_id, (e) => Ut(l, Y(l).client_id = e)), Yr(x, () => Y(l).client_secret, (e) => Ut(l, Y(l).client_secret = e)), Z("input", x, () => F(u, !0)), Z("click", S, () => F(d, !Y(d))), Z("click", T, h), Z("click", ee, g), Z("click", r, Qr(function(e) {
			ti.call(this, t, e);
		})), Z("click", n, h), $(e, n);
	};
	return Dr(ee, (e) => {
		Y(s) && e(te);
	}), $(e, x), He(b);
}
customElements.define("tidal-dashboard-card", ci(xi, { apiBase: {} }, [], []));
//#endregion
export { xi as default };
