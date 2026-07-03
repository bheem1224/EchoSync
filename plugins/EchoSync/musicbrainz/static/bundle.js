//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1;
function t() {
	e = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
t();
//#endregion
//#region node_modules/svelte/src/constants.js
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, g = Object.isExtensible, _ = () => {};
function v(e) {
	return e();
}
function y(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function b() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var x = 1024, S = 2048, C = 4096, w = 8192, ee = 16384, te = 32768, ne = 1 << 25, T = 65536, E = 1 << 19, re = 1 << 20, ie = 1 << 25, ae = 65536, oe = 1 << 21, se = 1 << 22, ce = 1 << 23, le = Symbol("$state"), ue = Symbol("legacy props"), de = Symbol(""), fe = Symbol("attributes"), pe = Symbol("class"), me = Symbol("style"), he = Symbol("text"), ge = Symbol("form reset"), _e = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), ve = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function ye(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function be() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function xe(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function Se(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Ce() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function we(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Te() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Ee() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function De(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Oe() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function ke() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ae() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function je() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Me() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Ne(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Pe() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var D = !1;
function Fe(e) {
	D = e;
}
var O;
function k(e) {
	if (e === null) throw Ne(), n;
	return O = e;
}
function Ie() {
	return k(/* @__PURE__ */ rn(O));
}
function A(e) {
	if (D) {
		if (/* @__PURE__ */ rn(O) !== null) throw Ne(), n;
		O = e;
	}
}
function Le(e = 1) {
	if (D) {
		for (var t = e, n = O; t--;) n = /* @__PURE__ */ rn(n);
		O = n;
	}
}
function Re(e = !0) {
	for (var t = 0, n = O;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ rn(n);
		e && n.remove(), n = i;
	}
}
function ze(e) {
	if (!e || e.nodeType !== 8) throw Ne(), n;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Be(e) {
	return e === this.v;
}
function Ve(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function He(e) {
	return !Ve(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var j = null;
function Ue(e) {
	j = e;
}
function We(t, n = !1, r) {
	j = {
		p: j,
		i: !1,
		c: null,
		e: null,
		s: t,
		x: null,
		r: G,
		l: e && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ge(e) {
	var t = j, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) yn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, j = t.p, e ?? {};
}
function Ke() {
	return !e || j !== null && j.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var qe = [];
function Je() {
	var e = qe;
	qe = [], y(e);
}
function Ye(e) {
	if (qe.length === 0 && !Tt) {
		var t = qe;
		queueMicrotask(() => {
			t === qe && Je();
		});
	}
	qe.push(e);
}
function Xe() {
	for (; qe.length > 0;) Je();
}
function Ze(e) {
	var t = G;
	if (t === null) return U.f |= ce, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Qe(e, t);
}
function Qe(e, t) {
	if (!(t !== null && t.f & 16384)) {
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
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var $e = ~(S | C | x);
function M(e, t) {
	e.f = e.f & $e | t;
}
function et(e) {
	e.f & 512 || e.deps === null ? M(e, x) : M(e, C);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function tt(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= ae, tt(t.deps));
}
function nt(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), tt(e.deps), M(e, x);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var rt = !1;
function it(e) {
	var t = rt;
	try {
		return rt = !1, [e(), rt];
	} finally {
		rt = t;
	}
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function at(e) {
	let t = 0, n = Wt(0), r;
	return () => {
		gn() && (Y(n), Tn(() => (t === 0 && (r = X(() => e(() => Jt(n)))), t += 1, () => {
			Ye(() => {
				--t, t === 0 && (r?.(), r = void 0, Jt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var ot = T | E;
function st(e, t, n, r) {
	new ct(e, t, n, r);
}
var ct = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = D ? O : null;
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
	#h = at(() => (this.#m = Wt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Dn(() => {
			if (D) {
				let e = this.#t;
				Ie();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, ot), D && (this.#e = O);
	}
	#g() {
		try {
			this.#a = V(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = V(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = V(() => e(this.#e)), Ye(() => {
			var e = this.#c = document.createDocumentFragment(), t = L();
			e.append(t), this.#a = this.#x(() => V(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Nn(this.#o, () => {
				this.#o = null;
			}), this.#b(N));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = V(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Ln(this.#a, e);
				let t = this.#n.pending;
				this.#o = V(() => t(this.#e));
			} else this.#b(N);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		nt(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = G, n = U, r = j;
		Un(this.#i), W(this.#i), Ue(this.#i.ctx);
		try {
			return jt.ensure(), e();
		} catch (e) {
			return Ze(e), null;
		} finally {
			Un(t), W(n), Ue(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && Nn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Ye(() => {
			this.#d = !1, this.#m && Kt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Y(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		N?.is_fork ? (this.#a && N.skip_effect(this.#a), this.#o && N.skip_effect(this.#o), this.#s && N.skip_effect(this.#s), N.oncommit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (H(this.#a), null), this.#o &&= (H(this.#o), null), this.#s &&= (H(this.#s), null), D && (k(this.#t), Le(), k(Re()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Pe();
				return;
			}
			r = !0, i && je(), this.#s !== null && Nn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				Qe(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return V(() => {
						var t = G;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return Qe(e, this.#i.parent), null;
				}
			}));
		};
		Ye(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				Qe(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => Qe(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function lt(e, t, n, r) {
	let i = Ke() ? pt : gt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = ut(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				Qe(e, s);
			}
			dt();
		}
	}
	var d = ft();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ ht(e))).then(u).catch((e) => Qe(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), dt();
	}) : f();
}
function ut() {
	var e = G, t = U, n = j, r = N;
	return function(i = !0) {
		Un(e), W(t), Ue(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function dt(e = !0) {
	Un(null), W(null), Ue(null), e && N?.deactivate();
}
function ft() {
	var e = G, t = e.b, n = N, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function pt(e) {
	var t = 2 | S;
	return G !== null && (G.f |= E), {
		ctx: j,
		deps: null,
		effects: null,
		equals: Be,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: r,
		wv: 0,
		parent: G,
		ac: null
	};
}
var mt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function ht(e, t, n) {
	let i = G;
	i === null && be();
	var a = void 0, o = Wt(r), s = !U, c = /* @__PURE__ */ new Set();
	return wn(() => {
		var t = G, n = b();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== _e && n.reject(e);
			}).finally(dt);
		} catch (e) {
			n.reject(e), dt();
		}
		var r = N;
		if (s) {
			if (t.f & 32768) var l = ft();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(mt);
			else for (let e of c.values()) e.reject(mt);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== mt && (r.activate(), t ? (o.f |= ce, Kt(o, t)) : (o.f & 8388608 && (o.f ^= ce), Kt(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), _n(() => {
		for (let e of c) e.reject(mt);
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
/*#__NO_SIDE_EFFECTS__*/
function gt(e) {
	let t = /* @__PURE__ */ pt(e);
	return t.equals = He, t;
}
function _t(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) H(t[n]);
	}
}
function vt(e) {
	var t, n = G, i = e.parent;
	if (!Bn && i !== null && e.v !== r && i.f & 24576) return Me(), e.v;
	Un(i);
	try {
		e.f &= ~ae, _t(e), t = er(e);
	} finally {
		Un(n);
	}
	return t;
}
function yt(e) {
	var t = vt(e);
	if (!e.equals(t) && (e.wv = Zn(), (!N?.is_fork || e.deps === null) && (N === null ? e.v = t : (N.capture(e, t, !0), Ct?.capture(e, t, !0)), e.deps === null))) {
		M(e, x);
		return;
	}
	Bn || (P === null ? et(e) : (gn() || N?.is_fork) && P.set(e, t));
}
function bt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(_e), t.fn !== null && (t.teardown = _), t.ac = null, nr(t, 0), kn(t));
}
function xt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && rr(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var St = null, N = null, Ct = null, P = null, wt = null, Tt = !1, Et = !1, Dt = null, Ot = null, kt = 0, At = 1, jt = class e {
	id = At++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = 0;
	#o = /* @__PURE__ */ new Map();
	#s = null;
	#c = [];
	#l = [];
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Map();
	#p = /* @__PURE__ */ new Set();
	is_fork = !1;
	#m = !1;
	constructor() {
		St === null ? St = this : (St.#n = this, this.#t = St), St = this;
	}
	#h() {
		if (this.is_fork) return !0;
		for (let n of this.#o.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#f.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#f.has(e) || this.#f.set(e, {
			d: [],
			m: []
		}), this.#p.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#f.get(e);
		if (n) {
			this.#f.delete(e);
			for (var r of n.d) M(r, S), t(r);
			for (r of n.m) M(r, C), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		this.#e = !0, kt++ > 1e3 && (this.#x(), Nt());
		for (let e of this.#u) this.#d.delete(e), M(e, S), this.schedule(e);
		for (let e of this.#d) M(e, C), this.schedule(e);
		let t = this.#c;
		this.#c = [], this.apply();
		var n = Dt = [], r = [], i = Ot = [];
		for (let e of t) try {
			this.#_(e, n, r);
		} catch (t) {
			throw Bt(e), this.#h() || this.discard(), t;
		}
		if (N = null, i.length > 0) {
			var a = e.ensure();
			for (let e of i) a.schedule(e);
		}
		if (Dt = null, Ot = null, this.#h()) {
			this.#b(r), this.#b(n);
			for (let [e, t] of this.#f) zt(e, t);
			i.length > 0 && N.#g();
			return;
		}
		let o = this.#v();
		if (o) {
			this.#b(r), this.#b(n), o.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), Ct = this, Ft(r), Ft(n), Ct = null, this.#s?.resolve();
		var s = N;
		if (this.#a === 0 && (this.#c.length === 0 || s !== null) && this.#x(), this.#c.length > 0) if (s !== null) {
			let e = s;
			e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
		} else s = this;
		s !== null && s.#g();
	}
	#_(e, t, n) {
		e.f ^= x;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = (i & 96) != 0;
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= x : i & 4 ? t.push(r) : Qn(r) && (i & 16 && this.#d.add(r), rr(r));
				var o = r.first;
				if (o !== null) {
					r = o;
					continue;
				}
			}
			for (; r !== null;) {
				var s = r.next;
				if (s !== null) {
					r = s;
					break;
				}
				r = r.parent;
			}
		}
	}
	#v() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#y(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_effects(e.#u, e.#d);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), M(i, S), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#x(), N = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) nt(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== r && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), P?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		N = this;
	}
	deactivate() {
		N = null, P = null;
	}
	flush() {
		try {
			Et = !0, N = this, this.#g();
		} finally {
			kt = 0, wt = null, Dt = null, Ot = null, Et = !1, N = null, P = null, Ht.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(mt);
		this.#x(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
	}
	increment(e, t) {
		if (this.#a += 1, e) {
			let e = this.#o.get(t) ?? 0;
			this.#o.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#a, e) {
			let e = this.#o.get(t) ?? 0;
			e === 1 ? this.#o.delete(t) : this.#o.set(t, e - 1);
		}
		this.#m || (this.#m = !0, Ye(() => {
			this.#m = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#u.add(t);
		for (let e of t) this.#d.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	settled() {
		return (this.#s ??= b()).promise;
	}
	static ensure() {
		if (N === null) {
			let t = N = new e();
			!Et && !Tt && Ye(() => {
				t.#e || t.flush();
			});
		}
		return N;
	}
	apply() {
		P = null;
	}
	schedule(e) {
		if (wt = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768)) {
			e.b.defer_effect(e);
			return;
		}
		for (var t = e; t.parent !== null;) {
			t = t.parent;
			var n = t.f;
			if (Dt !== null && t === G && (U === null || !(U.f & 2))) return;
			if (n & 96) {
				if (!(n & 1024)) return;
				t.f ^= x;
			}
		}
		this.#c.push(t);
	}
	#x() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null || (e.#n = t), t === null ? St = e : t.#t = e, this.linked = !1;
		}
	}
};
function Mt(e) {
	var t = Tt;
	Tt = !0;
	try {
		var n;
		for (e && (N !== null && !N.is_fork && N.flush(), n = e());;) {
			if (Xe(), N === null) return n;
			N.flush();
		}
	} finally {
		Tt = t;
	}
}
function Nt() {
	try {
		Te();
	} catch (e) {
		Qe(e, wt);
	}
}
var Pt = null;
function Ft(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Qn(r) && (Pt = /* @__PURE__ */ new Set(), rr(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Mn(r), Pt?.size > 0)) {
				Ht.clear();
				for (let e of Pt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) Pt.has(n) && (Pt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || rr(n);
					}
				}
				Pt.clear();
			}
		}
		Pt = null;
	}
}
function It(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? It(i, t, n, r) : e & 4194320 && !(e & 2048) && Lt(i, t, r) && (M(i, S), Rt(i));
	}
}
function Lt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (s.call(t, r)) return !0;
		if (r.f & 2 && Lt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function Rt(e) {
	N.schedule(e);
}
function zt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), M(e, x);
		for (var n = e.first; n !== null;) zt(n, t), n = n.next;
	}
}
function Bt(e) {
	M(e, x);
	for (var t = e.first; t !== null;) Bt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Vt = /* @__PURE__ */ new Set(), Ht = /* @__PURE__ */ new Map(), Ut = !1;
function Wt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Be,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Gt(e, t) {
	let n = Wt(e, t);
	return Gn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function F(t, n = !1, r = !0) {
	let i = Wt(t);
	return n || (i.equals = He), e && r && j !== null && j.l !== null && (j.l.s ??= []).push(i), i;
}
function I(e, t, n = !1) {
	return U !== null && (!Hn || U.f & 131072) && Ke() && U.f & 4325394 && (Wn === null || !Wn.has(e)) && Ae(), Kt(e, n ? Xt(t) : t, Ot);
}
function Kt(e, t, n = null) {
	if (!e.equals(t)) {
		Ht.set(e, Bn ? t : e.v);
		var r = jt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && vt(t), P === null && et(t);
		}
		e.wv = Zn(), Yt(e, S, n), Ke() && G !== null && G.f & 1024 && !(G.f & 96) && (J === null ? Kn([e]) : J.push(e)), !r.is_fork && Vt.size > 0 && !Ut && qt();
	}
	return t;
}
function qt() {
	Ut = !1;
	for (let e of Vt) {
		e.f & 1024 && M(e, C);
		let t;
		try {
			t = Qn(e);
		} catch {
			t = !0;
		}
		t && rr(e);
	}
	Vt.clear();
}
function Jt(e) {
	I(e, e.v + 1);
}
function Yt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ke(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & S) === 0;
			if (l && M(s, t), c & 131072) Vt.add(s);
			else if (c & 2) {
				var u = s;
				P?.delete(u), c & 65536 || (c & 512 && (G === null || !(G.f & 2097152)) && (s.f |= ae), Yt(u, C, n));
			} else if (l) {
				var d = s;
				c & 16 && Pt !== null && Pt.add(d), n === null ? Rt(d) : n.push(d);
			}
		}
	}
}
function Xt(e) {
	if (typeof e != "object" || !e || le in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ Gt(0), s = null, c = Yn, l = (e) => {
		if (Yn === c) return e();
		var t = U, n = Yn;
		W(null), Xn(c);
		var r = e();
		return W(t), Xn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ Gt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Oe();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Gt(r.value, s);
				return n.set(t, e), e;
			}) : I(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Gt(r, s));
					n.set(t, e), Jt(o);
				}
			} else I(i, r), Jt(o);
			return !0;
		},
		get(t, i, a) {
			if (i === le) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ Gt(Xt(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = Y(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var i = Reflect.getOwnPropertyDescriptor(e, t);
			if (i && "value" in i) {
				var a = n.get(t);
				a && (i.value = Y(a));
			} else if (i === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== r) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return i;
		},
		has(e, t) {
			if (t === le) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || G !== null && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ Gt(a ? Xt(e[t]) : r, s)), n.set(t, i)), Y(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Gt(r, s)), n.set(p + "", m)) : I(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Gt(void 0, s)), I(u, Xt(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => Xt(a));
				I(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && I(_, v + 1);
				}
				Jt(o);
			}
			return !0;
		},
		ownKeys(e) {
			Y(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== r;
			});
			for (var [i, a] of n) a.v !== r && !(i in e) && t.push(i);
			return t;
		},
		setPrototypeOf() {
			ke();
		}
	});
}
var Zt, Qt, $t, en;
function tn() {
	if (Zt === void 0) {
		Zt = window, Qt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		$t = d(t, "firstChild").get, en = d(t, "nextSibling").get, g(e) && (e[pe] = void 0, e[fe] = null, e[me] = void 0, e.__e = void 0), g(n) && (n[he] = void 0);
	}
}
function L(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function nn(e) {
	return $t.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function rn(e) {
	return en.call(e);
}
function R(e, t) {
	if (!D) return /* @__PURE__ */ nn(e);
	var n = /* @__PURE__ */ nn(O);
	if (n === null) n = O.appendChild(L());
	else if (t && n.nodeType !== 3) {
		var r = L();
		return n?.before(r), k(r), r;
	}
	return t && ln(n), k(n), n;
}
function an(e, t = !1) {
	if (!D) {
		var n = /* @__PURE__ */ nn(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ rn(n) : n;
	}
	if (t) {
		if (O?.nodeType !== 3) {
			var r = L();
			return O?.before(r), k(r), r;
		}
		ln(O);
	}
	return O;
}
function z(e, t = 1, n = !1) {
	let r = D ? O : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ rn(r);
	if (!D) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = L();
			return r === null ? i?.after(a) : r.before(a), k(a), a;
		}
		ln(r);
	}
	return k(r), r;
}
function on(e) {
	e.textContent = "";
}
function sn() {
	return !1;
}
function cn(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function ln(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var un = !1;
function dn() {
	un || (un = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ge]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function fn(e) {
	var t = U, n = G;
	W(null), Un(null);
	try {
		return e();
	} finally {
		W(t), Un(n);
	}
}
function pn(e, t, n, r = n) {
	e.addEventListener(t, () => fn(n));
	let i = e[ge];
	i ? e[ge] = () => {
		i(), r(!0);
	} : e[ge] = () => r(!0), dn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function mn(e) {
	G === null && (U === null && we(e), Ce()), Bn && Se(e);
}
function hn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function B(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= w);
	var r = {
		ctx: j,
		deps: null,
		nodes: null,
		f: e | S | 512,
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
	N?.register_created_effect(r);
	var i = r;
	if (e & 4) Dt === null ? jt.ensure().schedule(r) : Dt.push(r);
	else if (t !== null) {
		try {
			rr(r);
		} catch (e) {
			throw H(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= T));
	}
	if (i !== null && (i.parent = n, n !== null && hn(i, n), U !== null && U.f & 2 && !(e & 64))) {
		var a = U;
		(a.effects ??= []).push(i);
	}
	return r;
}
function gn() {
	return U !== null && !Hn;
}
function _n(e) {
	let t = B(8, null);
	return M(t, x), t.teardown = e, t;
}
function vn(e) {
	mn("$effect");
	var t = G.f;
	if (!U && t & 32 && j !== null && !j.i) {
		var n = j;
		(n.e ??= []).push(e);
	} else return yn(e);
}
function yn(e) {
	return B(4 | re, e);
}
function bn(e) {
	return mn("$effect.pre"), B(8 | re, e);
}
function xn(e) {
	jt.ensure();
	let t = B(64 | E, e);
	return () => {
		H(t);
	};
}
function Sn(e) {
	jt.ensure();
	let t = B(64 | E, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Nn(t, () => {
			H(t), n(void 0);
		}) : (H(t), n(void 0));
	});
}
function Cn(e) {
	return B(4, e);
}
function wn(e) {
	return B(se | E, e);
}
function Tn(e, t = 0) {
	return B(8 | t, e);
}
function En(e, t = [], n = [], r = []) {
	lt(r, t, n, (t) => {
		B(8, () => {
			e(...t.map(Y));
		});
	});
}
function Dn(e, t = 0) {
	return B(16 | t, e);
}
function V(e) {
	return B(32 | E, e);
}
function On(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Bn, n = U;
		Vn(!0), W(null);
		try {
			t.call(null);
		} finally {
			Vn(e), W(n);
		}
	}
}
function kn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && fn(() => {
			e.abort(_e);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : H(n, t), n = r;
	}
}
function An(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || H(t), t = n;
	}
}
function H(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (jn(e.nodes.start, e.nodes.end), n = !0), e.f |= ne, kn(e, t && !n), nr(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	On(e), e.f ^= ne, e.f |= ee;
	var i = e.parent;
	i !== null && i.first !== null && Mn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function jn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ rn(e);
		e.remove(), e = n;
	}
}
function Mn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Nn(e, t, n = !0) {
	var r = [];
	Pn(e, r, !0);
	var i = () => {
		n && H(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Pn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= w;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Pn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Fn(e) {
	In(e, !0);
}
function In(e, t) {
	if (e.f & 8192) {
		e.f ^= w, e.f & 1024 || (M(e, S), jt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			In(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Ln(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ rn(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Rn = null, zn = !1, Bn = !1;
function Vn(e) {
	Bn = e;
}
var U = null, Hn = !1;
function W(e) {
	U = e;
}
var G = null;
function Un(e) {
	G = e;
}
var Wn = null;
function Gn(e) {
	U !== null && (Wn ??= /* @__PURE__ */ new Set()).add(e);
}
var K = null, q = 0, J = null;
function Kn(e) {
	J = e;
}
var qn = 1, Jn = 0, Yn = Jn;
function Xn(e) {
	Yn = e;
}
function Zn() {
	return ++qn;
}
function Qn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~ae), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Qn(a) && yt(a), a.wv > e.wv) return !0;
		}
		t & 512 && P === null && M(e, x);
	}
	return !1;
}
function $n(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(Wn !== null && Wn.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? $n(a, t, !1) : t === a && (n ? M(a, S) : a.f & 1024 && M(a, C), Rt(a));
	}
}
function er(e) {
	var t = K, n = q, r = J, i = U, a = Wn, o = j, s = Hn, c = Yn, l = e.f;
	K = null, q = 0, J = null, U = l & 96 ? null : e, Wn = null, Ue(e.ctx), Hn = !1, Yn = ++Jn, e.ac !== null && (fn(() => {
		e.ac.abort(_e);
	}), e.ac = null);
	try {
		e.f |= oe;
		var u = e.fn, d = u();
		e.f |= te;
		var f = e.deps, p = N?.is_fork;
		if (K !== null) {
			var m;
			if (p || nr(e, q), f !== null && q > 0) for (f.length = q + K.length, m = 0; m < K.length; m++) f[q + m] = K[m];
			else e.deps = f = K;
			if (gn() && e.f & 512) for (m = q; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && q < f.length && (nr(e, q), f.length = q);
		if (Ke() && J !== null && !Hn && f !== null && !(e.f & 6146)) for (m = 0; m < J.length; m++) $n(J[m], e);
		if (i !== null && i !== e) {
			if (Jn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Jn;
			if (t !== null) for (let e of t) e.rv = Jn;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= ce), d;
	} catch (e) {
		return Ze(e);
	} finally {
		e.f ^= oe, K = t, q = n, J = r, U = i, Wn = a, Ue(o), Hn = s, Yn = c;
	}
}
function tr(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (K === null || !s.call(K, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512, c.f &= ~ae), c.v !== r && et(c), bt(c), nr(c, 0);
	}
}
function nr(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) tr(e, n[r]);
}
function rr(e) {
	var t = e.f;
	if (!(t & 16384)) {
		M(e, x);
		var n = G, r = zn;
		G = e, zn = !0;
		try {
			t & 16777232 ? An(e) : kn(e), On(e);
			var i = er(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = qn;
		} finally {
			zn = r, G = n;
		}
	}
}
async function ir() {
	await Promise.resolve(), Mt();
}
function Y(e) {
	var t = (e.f & 2) != 0;
	if (Rn?.add(e), U !== null && !Hn && !(G !== null && G.f & 16384) && (Wn === null || !Wn.has(e))) {
		var n = U.deps;
		if (U.f & 2097152) e.rv < Jn && (e.rv = Jn, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			U.deps ??= [], s.call(U.deps, e) || U.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [U] : s.call(r, U) || r.push(U);
		}
	}
	if (Bn && Ht.has(e)) return Ht.get(e);
	if (t) {
		var i = e;
		if (Bn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || or(i)) && (a = vt(i)), Ht.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !Hn && U !== null && (zn || (U.f & 512) != 0), c = (i.f & te) === 0;
		Qn(i) && (o && (i.f |= 512), yt(i)), o && !c && (xt(i), ar(i));
	}
	if (P?.has(e)) return P.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function ar(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (xt(t), ar(t));
}
function or(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Ht.has(t) || t.f & 2 && or(t)) return !0;
	return !1;
}
function X(e) {
	var t = Hn;
	try {
		return Hn = !0, e();
	} finally {
		Hn = t;
	}
}
function sr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (le in e) cr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && le in n && cr(n);
		}
	}
}
function cr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			cr(e[n], t);
		} catch {}
		let n = h(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = f(n);
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
var lr = Symbol("events"), ur = /* @__PURE__ */ new Set(), dr = /* @__PURE__ */ new Set();
function fr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || mr.call(t, e), !e.cancelBubble) return fn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Ye(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = fr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && _n(() => {
		t.removeEventListener(e, o, a);
	});
}
var pr = null;
function mr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	pr = e;
	var o = 0, s = pr === e && e[lr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[lr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		u(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var d = U, f = G;
		W(null), Un(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[lr]?.[r];
					h != null && (!a.disabled || e.target === a) && h.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				o++, a = o < i.length ? i[o] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[lr] = t, delete e.currentTarget, W(d), Un(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var hr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function gr(e) {
	return hr?.createHTML(e) ?? e;
}
function _r(e) {
	var t = cn("template");
	return t.innerHTML = gr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function vr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (D) return vr(O, null), O;
		i === void 0 && (i = _r(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ nn(i)));
		var t = r || Qt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ nn(t), s = t.lastChild;
			vr(o, s);
		} else vr(t, t);
		return t;
	};
}
function $(e, t) {
	if (D) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = O), Ie();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var yr = ["touchstart", "touchmove"];
function br(e) {
	return yr.includes(e);
}
function xr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[he] ??= e.nodeValue) && (e[he] = n, e.nodeValue = `${n}`);
}
function Sr(e, t) {
	return Tr(e, t);
}
function Cr(e, t) {
	tn(), t.intro = t.intro ?? !1;
	let r = t.target, i = D, a = O;
	try {
		for (var o = /* @__PURE__ */ nn(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ rn(o);
		if (!o) throw n;
		Fe(!0), k(o);
		let i = Tr(e, {
			...t,
			anchor: o
		});
		return Fe(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && Ee(), tn(), on(r), Fe(!1), Sr(e, t);
	} finally {
		Fe(i), k(a);
	}
}
var wr = /* @__PURE__ */ new Map();
function Tr(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	tn();
	var u = void 0, d = Sn(() => {
		var s = r ?? t.appendChild(L());
		st(s, { pending: () => {} }, (t) => {
			We({});
			var r = j;
			if (o && (r.c = o), a && (i.$$events = a), D && vr(t, null), u = e(t, i) || {}, D && (G.nodes.end = O, O === null || O.nodeType !== 8 || O.data !== "]")) throw Ne(), n;
			Ge();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = br(r);
					for (let e of [t, document]) {
						var a = wr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), wr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, mr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(ur)), dr.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = wr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, mr), n.delete(e), n.size === 0 && wr.delete(r)) : n.set(e, i);
			}
			dr.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return Er.set(u, d), u;
}
var Er = /* @__PURE__ */ new WeakMap();
function Dr(e, t) {
	let n = Er.get(e);
	return n ? (Er.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Or = class {
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
			if (n) Fn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Fn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (H(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Ln(r, t), t.append(L()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else H(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Nn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (H(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = N, r = sn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = L();
			i.append(a), this.#n.set(e, {
				effect: V(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, V(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else D && (this.anchor = O), this.#a(n);
	}
};
function kr(t) {
	j === null && ye("onMount"), e && j.l !== null ? Ar(j).m.push(t) : vn(() => {
		let e = X(t);
		if (typeof e == "function") return e;
	});
}
function Ar(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function jr(e, t, n = !1) {
	var r;
	D && (r = O, Ie());
	var i = new Or(e), a = n ? T : 0;
	function o(e, t) {
		if (D) {
			var n = ze(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Re();
				k(a), i.anchor = a, Fe(!1), i.ensure(e, t), Fe(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Dn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Mr(e, t) {
	return t;
}
function Nr(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		Nn(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Pr(e, c(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var l = r.length === 0 && n !== null;
		if (l) {
			var u = n, d = u.parentNode;
			on(d), d.append(u), e.items.clear();
		}
		Pr(e, t, !l);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Pr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= ie, Ln(a, document.createDocumentFragment())) : H(t[i], n);
	}
}
var Fr;
function Ir(e, t, n, r, i, o = null) {
	var s = e, l = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = D ? k(/* @__PURE__ */ nn(u)) : u.appendChild(L());
	}
	D && Ie();
	var d = null, f = /* @__PURE__ */ gt(() => {
		var e = n();
		return a(e) ? e : e == null ? [] : c(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Rr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= ie, Br(d, null, s)) : Fn(d) : Nn(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: Dn(() => {
			p = Y(f);
			var e = p.length;
			let a = !1;
			D && ze(s) === "[!" != (e === 0) && (s = Re(), k(s), Fe(!1), a = !0);
			for (var c = /* @__PURE__ */ new Set(), u = N, v = sn(), y = 0; y < e; y += 1) {
				D && O.nodeType === 8 && O.data === "]" && (s = O, a = !0, Fe(!1));
				var b = p[y], x = r(b, y), S = h ? null : l.get(x);
				S ? (S.v && Kt(S.v, b), S.i && Kt(S.i, y), v && u.unskip_effect(S.e)) : (S = zr(l, h ? s : Fr ??= L(), b, x, y, i, t, n), h || (S.e.f |= ie), l.set(x, S)), c.add(x);
			}
			if (e === 0 && o && !d && (h ? d = V(() => o(s)) : (d = V(() => o(Fr ??= L())), d.f |= ie)), e > c.size && xe("", "", ""), D && e > 0 && k(Re()), !h) if (m.set(u, c), v) {
				for (let [e, t] of l) c.has(e) || u.skip_effect(t.e);
				u.oncommit(g), u.ondiscard(_);
			} else g(u);
			a && Fe(!0), Y(f);
		}),
		flags: t,
		items: l,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, D && (s = O);
}
function Lr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Rr(e, t, n, r, i) {
	var a = (r & 8) != 0, o = t.length, s = e.items, l = Lr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Fn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= ie, _ === l) Br(_, null, n);
		else {
			var y = d ? d.next : l;
			_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Vr(e, d, _), Vr(e, _, y), Br(_, y, n), d = _, p = [], m = [], l = Lr(d.next);
			continue;
		}
		if (_ !== l) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Br(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Vr(e, S.prev, C.next), Vr(e, d, S), Vr(e, C, b), l = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Br(_, l, n), Vr(e, _.prev, _.next), Vr(e, _, d === null ? e.effect.first : d.next), Vr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; l !== null && l !== _;) (u ??= /* @__PURE__ */ new Set()).add(l), m.push(l), l = Lr(l.next);
			if (l === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, l = Lr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Pr(e, c(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (l !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; l !== null;) !(l.f & 8192) && l !== e.fallback && w.push(l), l = Lr(l.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			Nr(e, w, te);
		}
	}
	a && Ye(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function zr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Wt(n) : /* @__PURE__ */ F(n, !1, !1) : null, l = o & 2 ? Wt(i) : null;
	return {
		v: c,
		i: l,
		e: V(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Br(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ rn(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Vr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Hr(e, t) {
	Cn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = cn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var Ur = [..." 	\n\r\f\xA0\v﻿"];
function Wr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Ur.includes(r[o - 1])) && (s === r.length || Ur.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Gr(e, t, n, r, i, a) {
	var o = e[pe];
	if (D || o !== n || o === void 0) {
		var s = Wr(n, r, a);
		(!D || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[pe] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Kr = Symbol("is custom element"), qr = Symbol("is html"), Jr = ve ? "link" : "LINK", Yr = ve ? "progress" : "PROGRESS";
function Xr(e) {
	if (D) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Qr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Qr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ge] = n, Ye(n), dn();
	}
}
function Zr(e, t) {
	var n = $r(e);
	n.value === (n.value = t ?? void 0) || e.value === t && (t !== 0 || e.nodeName !== Yr) || (e.value = t ?? "");
}
function Qr(e, t, n, r) {
	var i = $r(e);
	D && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Jr) || i[t] !== (i[t] = n) && (t === "loading" && (e[de] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && ti(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function $r(e) {
	return e[fe] ??= {
		[Kr]: e.nodeName.includes("-"),
		[qr]: e.namespaceURI === i
	};
}
var ei = /* @__PURE__ */ new Map();
function ti(e) {
	var t = e.getAttribute("is") || e.nodeName, n = ei.get(t);
	if (n) return n;
	ei.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = h(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function ni(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	pn(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = ri(e) ? ii(a) : a, n(a), N !== null && r.add(N), await ir(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (D && e.defaultValue !== e.value || X(t) == null && e.value) && (n(ri(e) ? ii(e.value) : e.value), N !== null && r.add(N)), Tn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = N;
			if (r.has(i)) return;
		}
		ri(e) && n === ii(e.value) || e.type === "date" && !n && !e.value || n !== e.value && (e.value = n ?? "");
	});
}
function ri(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function ii(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function ai(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function oi(e = !1) {
	let t = j, n = t.l.u;
	if (!n) return;
	let r = () => sr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ pt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && bn(() => {
		si(t, r), y(n.b);
	}), vn(() => {
		let e = X(() => n.m.map(v));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && vn(() => {
		si(t, r), y(n.a);
	});
}
function si(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function ci(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of a(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function li(t, n, r, i) {
	var a = !e || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ pt(i), Y(u)) : (l && (l = !1, c = s ? X(i) : i), c);
	let p;
	if (o) {
		var m = le in t || ue in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, g = !1;
	o ? [h, g] = it(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && De(n), p(h)));
	var _ = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var v = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || v || g) && p(t ? _() : e), e) : _();
		});
	}
	var y = !1, b = (r & 1 ? pt : gt)(() => (y = !1, _()));
	o && Y(b);
	var x = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(b) : a && o ? Xt(e) : e;
			return I(b, n), y = !0, c !== void 0 && (c = n), e;
		}
		return Bn && y || x.f & 16384 ? b.v : Y(b);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function ui(e) {
	return new di(e);
}
var di = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ F(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Y(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === ue ? !0 : (Y(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return I(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? Cr : Sr)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), (!e?.props?.$$host || e.sync === !1) && Mt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || u(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Dr(this.#t);
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
}, fi;
typeof HTMLElement == "function" && (fi = class extends HTMLElement {
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
					let n = cn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = mi(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = pi(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = ui({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = xn(() => {
				Tn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = pi(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = pi(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return l(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function pi(e, t, n, r) {
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
function mi(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function hi(e, t, n, r, i, a) {
	let o = class extends fi {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return l(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return l(t).forEach((e) => {
		u(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = pi(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (d(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		u(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region MusicBrainzCard.svelte
var gi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-1ghyjz5\">Loading...</div>"), _i = /* @__PURE__ */ Q("<div class=\"redirect-copy-group svelte-1ghyjz5\"><input type=\"text\" class=\"input-field readonly svelte-1ghyjz5\" readonly=\"\"/> <button class=\"btn-primary svelte-1ghyjz5\">Copy</button></div>"), vi = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-1ghyjz5\">+ Add Account</button>"), yi = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-1ghyjz5\">✓ Authenticated</span>"), bi = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-1ghyjz5\">⚠ Not Authenticated</span>"), xi = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-1ghyjz5\">● Active</span>"), Si = /* @__PURE__ */ Q("<div class=\"account-item svelte-1ghyjz5\"><div class=\"account-info svelte-1ghyjz5\"><div class=\"account-name svelte-1ghyjz5\"> </div> <div class=\"account-badges svelte-1ghyjz5\"><!> <!></div></div> <div class=\"account-actions svelte-1ghyjz5\"><button class=\"link-btn svelte-1ghyjz5\"> </button> <button> </button> <button class=\"btn-danger svelte-1ghyjz5\">✕</button></div></div>"), Ci = /* @__PURE__ */ Q("<div class=\"empty-accounts svelte-1ghyjz5\">No accounts linked.</div>"), wi = /* @__PURE__ */ Q("<div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Server Configuration</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">API Base URL</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"https://musicbrainz.org/ws/2\"/> <p class=\"helper-text svelte-1ghyjz5\">Point this to a local MusicBrainz container for offline use.</p></label> <button class=\"btn-primary svelte-1ghyjz5\">Save Settings</button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">OAuth Credentials</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client ID</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"Enter Client ID\"/></label> <label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client Secret</span> <div class=\"password-wrapper svelte-1ghyjz5\"><input class=\"input-field svelte-1ghyjz5\"/> <button class=\"toggle-visibility svelte-1ghyjz5\"> </button></div></label> <button class=\"btn-primary svelte-1ghyjz5\"> </button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Redirect URI</h3> <button class=\"btn-ghost svelte-1ghyjz5\"> </button></div> <!></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\"> </h3> <!></div> <div class=\"accounts-list svelte-1ghyjz5\"></div></div>", 1), Ti = /* @__PURE__ */ Q("<div class=\"modal-overlay svelte-1ghyjz5\"><div class=\"modal-content svelte-1ghyjz5\"><div class=\"modal-header svelte-1ghyjz5\"><h3 class=\"modal-title svelte-1ghyjz5\">Add MusicBrainz Account</h3> <button class=\"close-btn svelte-1ghyjz5\">✕</button></div> <div class=\"modal-body svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Display Name</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"My Account\"/></label></div> <div class=\"modal-footer svelte-1ghyjz5\"><button class=\"btn-ghost svelte-1ghyjz5\">Cancel</button> <button class=\"btn-primary svelte-1ghyjz5\">Add</button></div></div></div>"), Ei = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-1ghyjz5\"><div class=\"card-header svelte-1ghyjz5\"><div class=\"header-left svelte-1ghyjz5\"><h2 class=\"card-title svelte-1ghyjz5\">MusicBrainz</h2> <span class=\"type-badge svelte-1ghyjz5\">Metadata Provider</span></div></div> <!></section> <!>", 1), Di = {
	hash: "svelte-1ghyjz5",
	code: ".plugin-card.svelte-1ghyjz5 {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-1ghyjz5 {display:flex;align-items:center;gap:12px;}.card-title.svelte-1ghyjz5 {margin:0;font-size:20px;font-weight:700;}.type-badge.svelte-1ghyjz5 {font-size:11px;padding:4px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-1ghyjz5 {padding:24px;text-align:center;color:var(--text-secondary, #cbd5e1);}.settings-section.svelte-1ghyjz5 {margin-bottom:24px;}.section-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}.section-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:600;}.form-grid.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-1ghyjz5 {font-size:13px;font-weight:500;color:var(--text-secondary, #cbd5e1);}.input-field.svelte-1ghyjz5 {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-1ghyjz5:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.input-field.readonly.svelte-1ghyjz5 {opacity:0.6;cursor:not-allowed;}.btn-primary.svelte-1ghyjz5 {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-1ghyjz5:hover:not(:disabled) {opacity:0.9;}.btn-primary.svelte-1ghyjz5:disabled {opacity:0.5;cursor:not-allowed;}.btn-ghost.svelte-1ghyjz5 {padding:8px 16px;background:rgba(255, 255, 255, 0.05);border:1px solid rgba(255, 255, 255, 0.1);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-1ghyjz5:hover {background:rgba(255, 255, 255, 0.1);}.btn-ghost.active.svelte-1ghyjz5 {border-color:var(--color-primary, #14b8a6);color:var(--color-primary, #14b8a6);}.btn-danger.svelte-1ghyjz5 {background:rgba(239, 68, 68, 0.15);color:#ef4444;border:none;padding:8px 12px;border-radius:6px;cursor:pointer;}.helper-text.svelte-1ghyjz5 {font-size:11px;color:var(--text-secondary, #cbd5e1);margin-top:4px;}.redirect-copy-group.svelte-1ghyjz5 {display:flex;gap:8px;align-items:stretch;}.redirect-copy-group.svelte-1ghyjz5 .input-field:where(.svelte-1ghyjz5) {flex:1;font-family:monospace;}.accounts-list.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.account-item.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid rgba(255, 255, 255, 0.05);border-radius:8px;}.account-info.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-1ghyjz5 {font-weight:600;font-size:14px;}.account-badges.svelte-1ghyjz5 {display:flex;gap:8px;}.status-badge.svelte-1ghyjz5 {font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-1ghyjz5 {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-1ghyjz5 {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-1ghyjz5 {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.account-actions.svelte-1ghyjz5 {display:flex;gap:12px;align-items:center;}.link-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:600;cursor:pointer;}.link-btn.svelte-1ghyjz5:hover {text-decoration:underline;}.password-wrapper.svelte-1ghyjz5 {position:relative;display:flex;align-items:center;width:100%;}.toggle-visibility.svelte-1ghyjz5 {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.modal-overlay.svelte-1ghyjz5 {position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px);}.modal-content.svelte-1ghyjz5 {background:#0f1216;border:1px solid var(--border-subtle, #1e293b);border-radius:12px;width:100%;max-width:440px;box-shadow:0 24px 48px rgba(0,0,0,0.5);}.modal-header.svelte-1ghyjz5 {padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;}.modal-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:700;}.close-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--text-secondary, #cbd5e1);font-size:20px;cursor:pointer;}.modal-body.svelte-1ghyjz5 {padding:20px;display:flex;flex-direction:column;gap:16px;}.modal-footer.svelte-1ghyjz5 {padding:16px 20px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;gap:12px;}.empty-accounts.svelte-1ghyjz5 {text-align:center;padding:16px;color:var(--text-secondary, #cbd5e1);font-size:13px;background:rgba(255, 255, 255, 0.02);border-radius:8px;border:1px dashed rgba(255, 255, 255, 0.1);}"
};
function Oi(e, t) {
	We(t, !1), Hr(e, Di);
	let n = li(t, "apiBase", 12, ""), r = /* @__PURE__ */ F(!0), i = /* @__PURE__ */ F([]), a = /* @__PURE__ */ F(""), o = /* @__PURE__ */ F(""), s = /* @__PURE__ */ F(""), c = /* @__PURE__ */ F(""), l = !1, u = !1, d = /* @__PURE__ */ F(!1), f = /* @__PURE__ */ F(!1), p = /* @__PURE__ */ F(!1), m = /* @__PURE__ */ F("https://musicbrainz.org/ws/2"), h = /* @__PURE__ */ F(!1), g = /* @__PURE__ */ F(""), _ = /* @__PURE__ */ F(!1);
	kr(async () => {
		await v(), I(r, !1);
	});
	async function v() {
		try {
			let e = await (await fetch(`${n()}/accounts`)).json();
			e && (I(i, e.accounts || []), I(a, e.redirect_uri || ""), l = e.client_id_configured || !1, u = e.client_secret_configured || !1, I(p, !!Y(a)));
			let t = await (await fetch(`${n()}/settings`)).json();
			t?.settings && I(m, t.settings.api_base_url || "https://musicbrainz.org/ws/2");
			let r = await (await fetch(`${n()}/credentials`)).json();
			r?.credentials && (I(o, r.credentials.client_id || ""), I(c, u ? "••••••••" : ""));
		} catch (e) {
			console.error("Failed to load MusicBrainz data:", e);
		}
	}
	async function y() {
		if (!Y(o).trim()) {
			console.error("Client ID is required");
			return;
		}
		let e = { client_id: Y(o) };
		if (Y(s).trim()) e.client_secret = Y(s);
		else if (!u) {
			console.error("Client Secret is required");
			return;
		}
		try {
			I(f, !0), await fetch(`${n()}/credentials`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ credentials: e })
			}), I(s, ""), await v();
		} catch (e) {
			console.error("Failed to save credentials:", e);
		} finally {
			I(f, !1);
		}
	}
	async function b() {
		try {
			await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ settings: { api_base_url: Y(m) } })
			}), console.log("MusicBrainz settings saved");
		} catch (e) {
			console.error("Failed to save settings:", e);
		}
	}
	function x() {
		I(g, ""), I(h, !0);
	}
	function S() {
		I(h, !1), I(g, "");
	}
	async function C() {
		let e = Y(g).trim();
		if (e) try {
			I(_, !0), await fetch(`${n()}/accounts`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ account_name: e })
			}), S(), await v();
		} catch (e) {
			console.error("Failed to add account:", e);
		} finally {
			I(_, !1);
		}
	}
	async function w(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/accounts/${e}`, { method: "DELETE" }), await v();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function ee(e, t) {
		try {
			await fetch(`${n()}/accounts/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), await v();
		} catch (e) {
			console.error("Failed to update account status:", e);
		}
	}
	async function te(e) {
		if (!l || !u) {
			alert("Save your Client ID and Secret first.");
			return;
		}
		try {
			let t = (await (await fetch(`${n()}/auth?account_id=${e}`)).json())?.auth_url;
			t && (window.open(t, "_blank", "noopener,noreferrer"), setTimeout(() => v(), 5e3));
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var ne = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Mt();
		}
	};
	oi();
	var T = Ei(), E = an(T), re = z(R(E), 2), ie = (e) => {
		$(e, gi());
	}, ae = (e) => {
		var t = wi(), n = an(t), r = z(R(n), 2), l = R(r), u = z(R(l), 2);
		Xr(u), Le(2), A(l);
		var h = z(l, 2);
		A(r), A(n);
		var g = z(n, 2), _ = z(R(g), 2), v = R(_), S = z(R(v), 2);
		Xr(S), A(v);
		var C = z(v, 2), ne = z(R(C), 2), T = R(ne);
		Xr(T);
		var E = z(T, 2), re = R(E, !0);
		A(E), A(ne), A(C);
		var ie = z(C, 2), ae = R(ie, !0);
		A(ie), A(_), A(g);
		var oe = z(g, 2), se = R(oe), ce = z(R(se), 2), le = R(ce, !0);
		A(ce), A(se);
		var ue = z(se, 2), de = (e) => {
			var t = _i(), n = R(t);
			Xr(n);
			var r = z(n, 2);
			A(t), En(() => Zr(n, Y(a))), Z("click", r, () => {
				navigator.clipboard.writeText(Y(a)), alert("Copied!");
			}), $(e, t);
		};
		jr(ue, (e) => {
			Y(p) || e(de);
		}), A(oe);
		var fe = z(oe, 2), pe = R(fe), me = R(pe), he = R(me);
		A(me);
		var ge = z(me, 2), _e = (e) => {
			var t = vi();
			Z("click", t, x), $(e, t);
		};
		jr(ge, (e) => {
			Y(i), X(() => Y(i).length < 10) && e(_e);
		}), A(pe);
		var ve = z(pe, 2);
		Ir(ve, 5, () => Y(i), Mr, (e, t) => {
			var n = Si(), r = R(n), i = R(r), a = R(i, !0);
			A(i);
			var o = z(i, 2), s = R(o), c = (e) => {
				$(e, yi());
			}, l = (e) => {
				$(e, bi());
			};
			jr(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = z(s, 2), d = (e) => {
				$(e, xi());
			};
			jr(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			}), A(o), A(r);
			var f = z(r, 2), p = R(f), m = R(p, !0);
			A(p);
			var h = z(p, 2);
			let g;
			var _ = R(h, !0);
			A(h);
			var v = z(h, 2);
			A(f), A(n), En(() => {
				xr(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), xr(m, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), g = Gr(h, 1, "btn-ghost svelte-1ghyjz5", null, g, { active: Y(t).is_active }), xr(_, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", p, () => te(Y(t).id)), Z("click", h, () => ee(Y(t).id, Y(t).is_active)), Z("click", v, () => w(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, Ci());
		}), A(ve), A(fe), En(() => {
			Qr(T, "type", Y(d) ? "text" : "password"), Qr(T, "placeholder", Y(c) || "Enter Client Secret"), xr(re, Y(d) ? "🙈" : "👁️"), ie.disabled = Y(f), xr(ae, Y(f) ? "Saving..." : "Save Credentials"), xr(le, Y(p) ? "Expand" : "Collapse"), xr(he, `Accounts (${(Y(i), X(() => Y(i).length)) ?? ""}/10)`);
		}), ni(u, () => Y(m), (e) => I(m, e)), Z("click", h, b), ni(S, () => Y(o), (e) => I(o, e)), ni(T, () => Y(s), (e) => I(s, e)), Z("click", E, () => I(d, !Y(d))), Z("click", ie, y), Z("click", ce, () => I(p, !Y(p))), $(e, t);
	};
	jr(re, (e) => {
		Y(r) ? e(ie) : e(ae, -1);
	}), A(E);
	var oe = z(E, 2), se = (e) => {
		var n = Ti(), r = R(n), i = R(r), a = z(R(i), 2);
		A(i);
		var o = z(i, 2), s = R(o), c = z(R(s), 2);
		Xr(c), A(s), A(o);
		var l = z(o, 2), u = R(l), d = z(u, 2);
		A(l), A(r), A(n), En(() => d.disabled = Y(_)), Z("click", a, S), ni(c, () => Y(g), (e) => I(g, e)), Z("click", u, S), Z("click", d, C), Z("click", r, ai(function(e) {
			ci.call(this, t, e);
		})), Z("click", n, S), $(e, n);
	};
	return jr(oe, (e) => {
		Y(h) && e(se);
	}), $(e, T), Ge(ne);
}
customElements.define("musicbrainz-dashboard-card", hi(Oi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
//#region MusicBrainzSettingsCard.svelte
var ki = /* @__PURE__ */ Q("<div class=\"loading-state svelte-18cwlk6\">Loading configuration…</div>"), Ai = /* @__PURE__ */ Q("<span class=\"status-tag success svelte-18cwlk6\">● Configured</span>"), ji = /* @__PURE__ */ Q("<div class=\"warning-box svelte-18cwlk6\">⚠ A User Token is required to enable contributions. Please enter your token above.</div>"), Mi = /* @__PURE__ */ Q("<div class=\"feedback error svelte-18cwlk6\"> </div>"), Ni = /* @__PURE__ */ Q("<div class=\"feedback success svelte-18cwlk6\">✓ Configuration saved successfully.</div>"), Pi = /* @__PURE__ */ Q("<div class=\"info-banner svelte-18cwlk6\"><p>MusicBrainz works out-of-the-box for metadata retrieval. An account is only needed for contributing data back to the community.</p></div> <div class=\"form-section svelte-18cwlk6\"><label class=\"field-label svelte-18cwlk6\" for=\"mb-user-token\">User Token / API Key <!></label> <p class=\"helper-text svelte-18cwlk6\">Obtain your personal access token from <a href=\"https://musicbrainz.org/account/applications\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"link svelte-18cwlk6\">musicbrainz.org/account/applications</a>.\n        Required for submitting ISRC codes and metadata corrections.</p> <div class=\"input-wrapper svelte-18cwlk6\"><input id=\"mb-user-token\" class=\"input-field svelte-18cwlk6\"/> <button type=\"button\" class=\"toggle-btn svelte-18cwlk6\"> </button></div></div> <div class=\"toggle-card svelte-18cwlk6\"><div class=\"toggle-header svelte-18cwlk6\"><p class=\"toggle-label svelte-18cwlk6\">Auto-Contribute Missing Data</p> <button type=\"button\" role=\"switch\" aria-label=\"Toggle auto-contribute\"><span class=\"switch-thumb svelte-18cwlk6\"></span></button></div> <p class=\"helper-text mt-2 svelte-18cwlk6\">When enabled, EchoSync will automatically submit missing acoustic fingerprints (AcoustID) and \n        ISRC data back to MusicBrainz during imports.</p> <!></div> <!> <!> <div class=\"actions svelte-18cwlk6\"><button class=\"btn-primary svelte-18cwlk6\"> </button></div>", 1), Fi = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-18cwlk6\"><div class=\"card-header svelte-18cwlk6\"><svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"accent-icon svelte-18cwlk6\"><circle cx=\"12\" cy=\"12\" r=\"10\"></circle><path d=\"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3\"></path><line x1=\"12\" y1=\"17\" x2=\"12.01\" y2=\"17\"></line></svg> <div><h2 class=\"card-title svelte-18cwlk6\">MusicBrainz Configuration</h2> <p class=\"card-subtitle svelte-18cwlk6\">Global music encyclopedia & metadata source</p></div> <span class=\"type-badge svelte-18cwlk6\">Metadata</span></div> <!></section>"), Ii = {
	hash: "svelte-18cwlk6",
	code: ".plugin-card.svelte-18cwlk6 {background:var(--bg-surface);backdrop-filter:blur(12px);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;margin-bottom:16px;color:var(--text-primary);}.card-header.svelte-18cwlk6 {display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle);}.accent-icon.svelte-18cwlk6 {color:var(--color-primary);}.card-title.svelte-18cwlk6 {margin:0;font-size:1.25rem;font-weight:600;line-height:1.2;}.card-subtitle.svelte-18cwlk6 {margin:4px 0 0;font-size:0.75rem;color:var(--text-muted);}.type-badge.svelte-18cwlk6 {margin-left:auto;font-size:11px;padding:4px 8px;background:rgba(16, 185, 129, 0.1);color:#10b981;border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-18cwlk6 {padding:20px;text-align:center;color:var(--text-muted);}.info-banner.svelte-18cwlk6 {margin-bottom:24px;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:8px;font-size:0.8125rem;color:var(--text-muted);line-height:1.4;}.form-section.svelte-18cwlk6 {margin-bottom:24px;}.field-label.svelte-18cwlk6 {display:block;font-size:0.875rem;font-weight:500;margin-bottom:4px;}.status-tag.success.svelte-18cwlk6 {margin-left:8px;font-size:11px;padding:2px 6px;background:rgba(16, 185, 129, 0.15);color:#10b981;border-radius:4px;}.helper-text.svelte-18cwlk6 {font-size:0.75rem;color:var(--text-muted);margin-bottom:8px;line-height:1.5;}.link.svelte-18cwlk6 {color:var(--color-primary);text-decoration:none;}.link.svelte-18cwlk6:hover {text-decoration:underline;}.input-wrapper.svelte-18cwlk6 {position:relative;display:flex;align-items:center;}.input-field.svelte-18cwlk6 {width:100%;padding:10px 14px;padding-right:40px;background:rgba(0, 0, 0, 0.2);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);color:var(--text-primary);font-size:0.875rem;transition:border-color 0.2s;}.input-field.svelte-18cwlk6:focus {outline:none;border-color:var(--color-primary);}.toggle-btn.svelte-18cwlk6 {position:absolute;right:12px;background:transparent;border:none;cursor:pointer;font-size:1.1rem;opacity:0.6;transition:opacity 0.2s;}.toggle-btn.svelte-18cwlk6:hover {opacity:1;}.toggle-card.svelte-18cwlk6 {margin-bottom:24px;padding:16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);}.toggle-header.svelte-18cwlk6 {display:flex;justify-content:space-between;align-items:center;}.toggle-label.svelte-18cwlk6 {margin:0;font-size:0.875rem;font-weight:600;}.switch.svelte-18cwlk6 {position:relative;width:44px;height:24px;background:rgba(255, 255, 255, 0.2);border-radius:999px;border:none;cursor:pointer;transition:background 0.2s;}.switch.active.svelte-18cwlk6 {background:var(--color-primary, #14b8a6);}.switch-thumb.svelte-18cwlk6 {position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:transform 0.2s;}.switch.active.svelte-18cwlk6 .switch-thumb:where(.svelte-18cwlk6) {transform:translateX(20px);}.warning-box.svelte-18cwlk6 {margin-top:12px;padding:8px 12px;background:rgba(245, 158, 11, 0.1);border:1px solid rgba(245, 158, 11, 0.2);border-radius:6px;font-size:11px;color:#fbbf24;line-height:1.4;}.feedback.svelte-18cwlk6 {margin-bottom:16px;padding:10px 14px;border-radius:var(--radius, 12px);font-size:0.875rem;}.feedback.error.svelte-18cwlk6 {background:rgba(239, 68, 68, 0.1);border:1px solid #ef4444;color:#ef4444;}.feedback.success.svelte-18cwlk6 {background:rgba(16, 185, 129, 0.1);border:1px solid #10b981;color:#10b981;}.actions.svelte-18cwlk6 {display:flex;justify-content:flex-end;}.btn-primary.svelte-18cwlk6 {padding:10px 24px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);font-weight:600;border:none;border-radius:var(--radius, 12px);cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-18cwlk6:hover:not(:disabled) {opacity:0.9;box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-18cwlk6:active:not(:disabled) {transform:scale(0.98);}.btn-primary.svelte-18cwlk6:disabled {opacity:0.5;cursor:not-allowed;}.mt-2.svelte-18cwlk6 {margin-top:8px;}"
};
function Li(e, t) {
	We(t, !1), Hr(e, Ii);
	let n = li(t, "apiBase", 12, ""), r = /* @__PURE__ */ F(!0), i = /* @__PURE__ */ F(!1), a = /* @__PURE__ */ F(!1), o = /* @__PURE__ */ F(""), s = /* @__PURE__ */ F(""), c = /* @__PURE__ */ F(!1), l = /* @__PURE__ */ F(!1), u = /* @__PURE__ */ F(!1);
	kr(async () => {
		await d(), I(r, !1);
	});
	async function d() {
		try {
			n();
			let e = await fetch(`${n()}/config`);
			if (e.ok) {
				let t = await e.json();
				I(c, t.token_configured ?? !1), I(u, t.auto_contribute ?? !1), Y(c) && I(s, "");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Failed to load config:", e);
		}
	}
	async function f() {
		let e = { auto_contribute: Y(u) };
		if (Y(s).trim()) e.user_token = Y(s).trim();
		else if (Y(u) && !Y(c)) {
			I(o, "A User Token is required to enable auto-contributions.");
			return;
		}
		I(o, ""), I(i, !0), I(a, !1);
		try {
			n();
			let t = await fetch(`${n()}/config`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			});
			if (t.ok) {
				let e = await t.json();
				I(c, e.token_configured ?? Y(c)), I(s, ""), I(a, !0), dispatchEvent(new CustomEvent("musicbrainz-config-saved", {
					bubbles: !0,
					composed: !0,
					detail: {
						auto_contribute: Y(u),
						token_configured: Y(c)
					}
				})), setTimeout(() => I(a, !1), 3e3);
			} else {
				let e = await t.json().catch(() => ({}));
				I(o, e.error || "Failed to save configuration.");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Save error:", e), I(o, "Network error while saving. Please try again.");
		} finally {
			I(i, !1);
		}
	}
	var p = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Mt();
		}
	};
	oi();
	var m = Fi(), h = z(R(m), 2), g = (e) => {
		$(e, ki());
	}, _ = (e) => {
		var t = Pi(), n = z(an(t), 2), r = R(n), d = z(R(r)), p = (e) => {
			$(e, Ai());
		};
		jr(d, (e) => {
			Y(c) && e(p);
		}), A(r);
		var m = z(r, 4), h = R(m);
		Xr(h);
		var g = z(h, 2), _ = R(g, !0);
		A(g), A(m), A(n);
		var v = z(n, 2), y = R(v), b = z(R(y), 2);
		A(y);
		var x = z(y, 4), S = (e) => {
			$(e, ji());
		};
		jr(x, (e) => {
			Y(u) && !Y(c) && !Y(s) && e(S);
		}), A(v);
		var C = z(v, 2), w = (e) => {
			var t = Mi(), n = R(t);
			A(t), En(() => xr(n, `⚠ ${Y(o) ?? ""}`)), $(e, t);
		};
		jr(C, (e) => {
			Y(o) && e(w);
		});
		var ee = z(C, 2), te = (e) => {
			$(e, Ni());
		};
		jr(ee, (e) => {
			Y(a) && e(te);
		});
		var ne = z(ee, 2), T = R(ne), E = R(T, !0);
		A(T), A(ne), En(() => {
			Qr(h, "type", Y(l) ? "text" : "password"), Qr(h, "placeholder", Y(c) ? "••••••••  (leave blank to keep current)" : "Enter your MusicBrainz user token"), Qr(g, "title", Y(l) ? "Hide token" : "Show token"), Qr(g, "aria-label", Y(l) ? "Hide token" : "Show token"), xr(_, Y(l) ? "🙈" : "👁️"), Qr(b, "aria-checked", Y(u)), Gr(b, 1, `switch ${Y(u) ? "active" : ""}`, "svelte-18cwlk6"), T.disabled = Y(i), xr(E, Y(i) ? "Saving…" : "Save Settings");
		}), ni(h, () => Y(s), (e) => I(s, e)), Z("click", g, () => I(l, !Y(l))), Z("click", b, () => I(u, !Y(u))), Z("click", T, f), $(e, t);
	};
	return jr(h, (e) => {
		Y(r) ? e(g) : e(_, -1);
	}), A(m), $(e, m), Ge(p);
}
customElements.define("musicbrainz-settings-card", hi(Li, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
