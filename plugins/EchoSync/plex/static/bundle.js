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
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, ee = Object.isExtensible, g = () => {};
function te(e) {
	return e();
}
function ne(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function _() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var v = 1024, y = 2048, b = 4096, re = 8192, ie = 16384, ae = 32768, oe = 1 << 25, se = 65536, x = 1 << 19, ce = 1 << 20, le = 65536, ue = 1 << 21, de = 1 << 22, fe = 1 << 23, pe = Symbol("$state"), me = Symbol("legacy props"), he = Symbol(""), ge = Symbol("attributes"), _e = Symbol("class"), ve = Symbol("style"), ye = Symbol("text"), be = Symbol("form reset"), xe = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), Se = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function Ce(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function we() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Te(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Ee() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function De(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Oe() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function ke() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Ae(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function je() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Me() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ne() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Pe() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Fe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Ie(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Le() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var S = !1;
function Re(e) {
	S = e;
}
var C;
function w(e) {
	if (e === null) throw Ie(), n;
	return C = e;
}
function ze() {
	return w(/* @__PURE__ */ F(C));
}
function T(e) {
	if (S) {
		if (/* @__PURE__ */ F(C) !== null) throw Ie(), n;
		C = e;
	}
}
function Be(e = 1) {
	if (S) {
		for (var t = e, n = C; t--;) n = /* @__PURE__ */ F(n);
		C = n;
	}
}
function Ve(e = !0) {
	for (var t = 0, n = C;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ F(n);
		e && n.remove(), n = i;
	}
}
function He(e) {
	if (!e || e.nodeType !== 8) throw Ie(), n;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Ue(e) {
	return e === this.v;
}
function We(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ge(e) {
	return !We(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var E = null;
function Ke(e) {
	E = e;
}
function qe(t, n = !1, r) {
	E = {
		p: E,
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
function Je(e) {
	var t = E, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) vn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, E = t.p, e ?? {};
}
function Ye() {
	return !e || E !== null && E.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Xe = [];
function Ze() {
	var e = Xe;
	Xe = [], ne(e);
}
function D(e) {
	if (Xe.length === 0 && !jt) {
		var t = Xe;
		queueMicrotask(() => {
			t === Xe && Ze();
		});
	}
	Xe.push(e);
}
function Qe() {
	for (; Xe.length > 0;) Ze();
}
function $e(e) {
	var t = G;
	if (t === null) return H.f |= fe, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	et(e, t);
}
function et(e, t) {
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
var tt = ~(y | b | v);
function O(e, t) {
	e.f = e.f & tt | t;
}
function nt(e) {
	e.f & 512 || e.deps === null ? O(e, v) : O(e, b);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function rt(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= le, rt(t.deps));
}
function it(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), rt(e.deps), O(e, v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var at = !1;
function ot(e) {
	var t = at;
	try {
		return at = !1, [e(), at];
	} finally {
		at = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var st = !1;
function ct() {
	st || (st = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[be]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function lt(e) {
	var t = H, n = G;
	W(null), K(null);
	try {
		return e();
	} finally {
		W(t), K(n);
	}
}
function ut(e, t, n, r = n) {
	e.addEventListener(t, () => lt(n));
	let i = e[be];
	i ? e[be] = () => {
		i(), r(!0);
	} : e[be] = () => r(!0), ct();
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function dt(e) {
	let t = 0, n = Yt(0), r;
	return () => {
		hn() && (Z(n), wn(() => (t === 0 && (r = nr(() => e(() => Qt(n)))), t += 1, () => {
			D(() => {
				--t, t === 0 && (r?.(), r = void 0, Qt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var ft = se | x;
function pt(e, t, n, r) {
	new mt(e, t, n, r);
}
var mt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = S ? C : null;
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
	#h = dt(() => (this.#m = Yt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = En(() => {
			if (S) {
				let e = this.#t;
				ze();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#y() : this.#g();
			} else this.#b();
		}, ft), S && (this.#e = C);
	}
	#g() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#v(e);
		D(r), t && (this.#s = z(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#v(e) {
		var t = !1, n = !1;
		let r = () => {
			if (t) {
				Le();
				return;
			}
			t = !0, n && Pe(), this.#s !== null && Mn(this.#s, () => {
				this.#s = null;
			}), this.#S(() => {
				this.#b();
			});
		};
		return {
			reset: r,
			invoke_onerror: () => {
				try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					et(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), D(() => {
			var e = this.#c = document.createDocumentFragment(), t = sn();
			e.append(t), this.#a = this.#S(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Mn(this.#o, () => {
				this.#o = null;
			}), this.#x(k));
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				In(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#x(k);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		it(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = G, n = H, r = E;
		K(this.#i), W(this.#i), Ke(this.#i.ctx);
		try {
			return Lt.ensure(), e();
		} catch (e) {
			return $e(e), null;
		} finally {
			K(t), W(n), Ke(r);
		}
	}
	#C(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#C(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#x(t), this.#o && Mn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, D(() => {
			this.#d = !1, this.#m && Xt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Z(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		k?.is_fork ? (this.#a && k.skip_effect(this.#a), this.#o && k.skip_effect(this.#o), this.#s && k.skip_effect(this.#s), k.oncommit(() => {
			this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), S && (w(this.#t), Be(), w(Ve()));
		let t = this.#n.failed, n = (e) => {
			let { reset: n, invoke_onerror: r } = this.#v(e);
			r(), t && (this.#s = this.#S(() => {
				try {
					return z(() => {
						var r = G;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return et(e, this.#i.parent), null;
				}
			}));
		};
		D(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				et(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => et(e, this.#i && this.#i.parent)) : n(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function ht(e, t, n, r) {
	let i = Ye() ? yt : St;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = gt(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				et(e, s);
			}
			_t();
		}
	}
	var d = vt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ xt(e))).then(u).catch((e) => et(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), _t();
	}) : f();
}
function gt() {
	var e = G, t = H, n = E, r = k;
	return function(i = !0) {
		K(e), W(t), Ke(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function _t(e = !0) {
	K(null), W(null), Ke(null), e && k?.deactivate();
}
function vt() {
	var e = G, t = e.b, n = k, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function yt(e) {
	var t = 2 | y;
	return G !== null && (G.f |= x), {
		ctx: E,
		deps: null,
		effects: null,
		equals: Ue,
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
var bt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function xt(e, t, n) {
	let i = G;
	i === null && we();
	var a = void 0, o = Yt(r), s = !H, c = /* @__PURE__ */ new Set();
	return Cn(() => {
		var t = G, n = _();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== xe && n.reject(e);
			}).finally(_t);
		} catch (e) {
			n.reject(e), _t();
		}
		var r = k;
		if (s) {
			if (t.f & 32768) var l = vt();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(bt);
			else for (let e of c.values()) e.reject(bt);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== bt && (r.activate(), t ? (o.f |= fe, Xt(o, t)) : (o.f & 8388608 && (o.f ^= fe), Xt(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), gn(() => {
		for (let e of c) e.reject(bt);
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
function St(e) {
	let t = /* @__PURE__ */ yt(e);
	return t.equals = Ge, t;
}
function Ct(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function wt(e) {
	var t, n = G, i = e.parent;
	if (!V && i !== null && e.v !== r && i.f & 24576) return Fe(), e.v;
	K(i);
	try {
		e.f &= ~le, Ct(e), t = Yn(e);
	} finally {
		K(n);
	}
	return t;
}
function Tt(e) {
	var t = wt(e);
	if (!e.equals(t) && (e.wv = Kn(), (!k?.is_fork || e.deps === null) && (k === null ? e.v = t : (k.capture(e, t, !0), kt?.capture(e, t, !0)), e.deps === null))) {
		O(e, v);
		return;
	}
	V || (A === null ? nt(e) : (hn() || k?.is_fork) && A.set(e, t));
}
function Et(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && lt(() => {
		t.ac.abort(xe), t.ac = null;
	}), t.fn !== null && (t.teardown = g), Zn(t, 0), On(t));
}
function Dt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && Qn(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var Ot = null, k = null, kt = null, A = null, At = null, jt = !1, Mt = !1, Nt = null, Pt = null, Ft = 0, It = 1, Lt = class e {
	id = It++;
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
		Ot === null ? Ot = this : (Ot.#n = this, this.#t = Ot), Ot = this;
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
			for (var r of n.d) O(r, y), t(r);
			for (r of n.m) O(r, b), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		this.#e = !0, Ft++ > 1e3 && (this.#x(), zt());
		for (let e of this.#u) this.#d.delete(e), O(e, y), this.schedule(e);
		for (let e of this.#d) O(e, b), this.schedule(e);
		let t = this.#c;
		this.#c = [], this.apply();
		var n = Nt = [], r = [], i = Pt = [];
		for (let e of t) try {
			this.#_(e, n, r);
		} catch (t) {
			throw Gt(e), this.#h() || this.discard(), t;
		}
		if (k = null, i.length > 0) {
			var a = e.ensure();
			for (let e of i) a.schedule(e);
		}
		if (Nt = null, Pt = null, this.#h()) {
			this.#b(r), this.#b(n);
			for (let [e, t] of this.#f) Wt(e, t);
			i.length > 0 && k.#g();
			return;
		}
		let o = this.#v();
		if (o) {
			this.#b(r), this.#b(n), o.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), kt = this, Bt(r), Bt(n), kt = null, this.#s?.resolve();
		var s = k;
		if (this.#a === 0 && (this.#c.length === 0 || s !== null) && this.#x(), this.#c.length > 0) if (s !== null) {
			let e = s;
			e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
		} else s = this;
		s !== null && s.#g();
	}
	#_(e, t, n) {
		e.f ^= v;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = (i & 96) != 0;
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= v : i & 4 ? t.push(r) : qn(r) && (i & 16 && this.#d.add(r), Qn(r));
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
			if (n !== null && !(e.f & 2 && !(e.f & 6144))) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), O(i, y), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#x(), k = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) it(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== r && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), A?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		k = this;
	}
	deactivate() {
		k = null, A = null;
	}
	flush() {
		try {
			Mt = !0, k = this, this.#g();
		} finally {
			Ft = 0, At = null, Nt = null, Pt = null, Mt = !1, k = null, A = null, qt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(bt);
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
		this.#m || (this.#m = !0, D(() => {
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
		return (this.#s ??= _()).promise;
	}
	static ensure() {
		if (k === null) {
			let t = k = new e();
			!Mt && !jt && D(() => {
				t.#e || t.flush();
			});
		}
		return k;
	}
	apply() {
		A = null;
	}
	schedule(e) {
		if (At = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768)) {
			e.b.defer_effect(e);
			return;
		}
		for (var t = e; t.parent !== null;) {
			t = t.parent;
			var n = t.f;
			if (Nt !== null && t === G && (H === null || !(H.f & 2))) return;
			if (n & 96) {
				if (!(n & 1024)) return;
				t.f ^= v;
			}
		}
		this.#c.push(t);
	}
	#x() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null || (e.#n = t), t === null ? Ot = e : t.#t = e, this.linked = !1;
		}
	}
};
function Rt(e) {
	var t = jt;
	jt = !0;
	try {
		var n;
		for (e && (k !== null && !k.is_fork && k.flush(), n = e());;) {
			if (Qe(), k === null) return n;
			k.flush();
		}
	} finally {
		jt = t;
	}
}
function zt() {
	try {
		Oe();
	} catch (e) {
		et(e, At);
	}
}
var j = null;
function Bt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && qn(r) && (j = /* @__PURE__ */ new Set(), Qn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && jn(r), j?.size > 0)) {
				qt.clear();
				for (let e of j) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) j.has(n) && (j.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Qn(n);
					}
				}
				j.clear();
			}
		}
		j = null;
	}
}
function Vt(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? Vt(i, t, n, r) : e & 4194320 && !(e & 2048) && Ht(i, t, r) && (O(i, y), Ut(i));
	}
}
function Ht(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (s.call(t, r)) return !0;
		if (r.f & 2 && Ht(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function Ut(e) {
	k.schedule(e);
}
function Wt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), O(e, v);
		for (var n = e.first; n !== null;) Wt(n, t), n = n.next;
	}
}
function Gt(e) {
	O(e, v);
	for (var t = e.first; t !== null;) Gt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Kt = /* @__PURE__ */ new Set(), qt = /* @__PURE__ */ new Map(), Jt = !1;
function Yt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Ue,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function M(e, t) {
	let n = Yt(e, t);
	return Bn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function N(t, n = !1, r = !0) {
	let i = Yt(t);
	return n || (i.equals = Ge), e && r && E !== null && E.l !== null && (E.l.s ??= []).push(i), i;
}
function P(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && Ye() && H.f & 4325394 && (q === null || !q.has(e)) && Ne(), Xt(e, n ? en(t) : t, Pt);
}
function Xt(e, t, n = null) {
	if (!e.equals(t)) {
		qt.set(e, V ? t : e.v);
		var r = Lt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && wt(t), A === null && nt(t);
		}
		e.wv = Kn(), $t(e, y, n), Ye() && G !== null && G.f & 1024 && !(G.f & 96) && (X === null ? Vn([e]) : X.push(e)), !r.is_fork && Kt.size > 0 && !Jt && Zt();
	}
	return t;
}
function Zt() {
	Jt = !1;
	for (let e of Kt) {
		e.f & 1024 && O(e, b);
		let t;
		try {
			t = qn(e);
		} catch {
			t = !0;
		}
		t && Qn(e);
	}
	Kt.clear();
}
function Qt(e) {
	P(e, e.v + 1);
}
function $t(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ye(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & y) === 0;
			if (l && O(s, t), c & 131072) Kt.add(s);
			else if (c & 2) {
				var u = s;
				A?.delete(u), c & 65536 || (c & 512 && (G === null || !(G.f & 2097152)) && (s.f |= le), $t(u, b, n));
			} else if (l) {
				var d = s;
				c & 16 && j !== null && j.add(d), n === null ? Ut(d) : n.push(d);
			}
		}
	}
}
function en(e) {
	if (typeof e != "object" || !e || pe in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ M(0), s = null, c = Wn, l = (e) => {
		if (Wn === c) return e();
		var t = H, n = Wn;
		W(null), Gn(c);
		var r = e();
		return W(t), Gn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ M(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && je();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ M(r.value, s);
				return n.set(t, e), e;
			}) : P(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ M(r, s));
					n.set(t, e), Qt(o);
				}
			} else P(i, r), Qt(o);
			return !0;
		},
		get(t, i, a) {
			if (i === pe) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ M(en(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = Z(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var i = Reflect.getOwnPropertyDescriptor(e, t);
			if (i && "value" in i) {
				var a = n.get(t);
				a && (i.value = Z(a));
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
			if (t === pe) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || G !== null && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ M(a ? en(e[t]) : r, s)), n.set(t, i)), Z(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ M(r, s)), n.set(p + "", m)) : P(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ M(void 0, s)), P(u, en(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => en(a));
				P(u, h);
			}
			var ee = Reflect.getOwnPropertyDescriptor(e, t);
			if (ee?.set && ee.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var g = n.get("length"), te = Number(t);
					Number.isInteger(te) && te >= g.v && P(g, te + 1);
				}
				Qt(o);
			}
			return !0;
		},
		ownKeys(e) {
			Z(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== r;
			});
			for (var [i, a] of n) a.v !== r && !(i in e) && t.push(i);
			return t;
		},
		setPrototypeOf() {
			Me();
		}
	});
}
var tn, nn, rn, an;
function on() {
	if (tn === void 0) {
		tn = window, nn = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		rn = d(t, "firstChild").get, an = d(t, "nextSibling").get, ee(e) && (e[_e] = void 0, e[ge] = null, e[ve] = void 0, e.__e = void 0), ee(n) && (n[ye] = void 0);
	}
}
function sn(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function cn(e) {
	return rn.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function F(e) {
	return an.call(e);
}
function I(e, t) {
	if (!S) return /* @__PURE__ */ cn(e);
	var n = /* @__PURE__ */ cn(C);
	if (n === null) n = C.appendChild(sn());
	else if (t && n.nodeType !== 3) {
		var r = sn();
		return n?.before(r), w(r), r;
	}
	return t && fn(n), w(n), n;
}
function L(e, t = 1, n = !1) {
	let r = S ? C : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ F(r);
	if (!S) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = sn();
			return r === null ? i?.after(a) : r.before(a), w(a), a;
		}
		fn(r);
	}
	return w(r), r;
}
function ln(e) {
	e.textContent = "";
}
function un() {
	return !1;
}
function dn(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function fn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function pn(e) {
	G === null && (H === null && De(e), Ee()), V && Te(e);
}
function mn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function R(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= re);
	var r = {
		ctx: E,
		deps: null,
		nodes: null,
		f: e | y | 512,
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
	k?.register_created_effect(r);
	var i = r;
	if (e & 4) Nt === null ? Lt.ensure().schedule(r) : Nt.push(r);
	else if (t !== null) {
		try {
			Qn(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= se));
	}
	if (i !== null && (i.parent = n, n !== null && mn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function hn() {
	return H !== null && !U;
}
function gn(e) {
	let t = R(8, null);
	return O(t, v), t.teardown = e, t;
}
function _n(e) {
	pn("$effect");
	var t = G.f;
	if (!H && t & 32 && E !== null && !E.i) {
		var n = E;
		(n.e ??= []).push(e);
	} else return vn(e);
}
function vn(e) {
	return R(4 | ce, e);
}
function yn(e) {
	return pn("$effect.pre"), R(8 | ce, e);
}
function bn(e) {
	Lt.ensure();
	let t = R(64 | x, e);
	return () => {
		B(t);
	};
}
function xn(e) {
	Lt.ensure();
	let t = R(64 | x, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Mn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function Sn(e) {
	return R(4, e);
}
function Cn(e) {
	return R(de | x, e);
}
function wn(e, t = 0) {
	return R(8 | t, e);
}
function Tn(e, t = [], n = [], r = []) {
	ht(r, t, n, (t) => {
		R(8, () => {
			e(...t.map(Z));
		});
	});
}
function En(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | x, e);
}
function Dn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = V, n = H;
		zn(!0), W(null);
		try {
			t.call(null);
		} finally {
			zn(e), W(n);
		}
	}
}
function On(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && lt(() => {
			e.abort(xe);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function kn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (An(e.nodes.start, e.nodes.end), n = !0), e.f |= oe, On(e, t && !n), Zn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Dn(e), e.f ^= oe, e.f |= ie;
	var i = e.parent;
	i !== null && i.first !== null && jn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function An(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ F(e);
		e.remove(), e = n;
	}
}
function jn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Mn(e, t, n = !0) {
	var r = [];
	Nn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Nn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= re;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Nn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Pn(e) {
	Fn(e, !0);
}
function Fn(e, t) {
	if (e.f & 8192) {
		e.f ^= re, e.f & 1024 || (O(e, y), Lt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Fn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function In(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ F(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Ln = null, Rn = !1, V = !1;
function zn(e) {
	V = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function K(e) {
	G = e;
}
var q = null;
function Bn(e) {
	H !== null && (q ??= /* @__PURE__ */ new Set()).add(e);
}
var J = null, Y = 0, X = null;
function Vn(e) {
	X = e;
}
var Hn = 1, Un = 0, Wn = Un;
function Gn(e) {
	Wn = e;
}
function Kn() {
	return ++Hn;
}
function qn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~le), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (qn(a) && Tt(a), a.wv > e.wv) return !0;
		}
		t & 512 && A === null && O(e, v);
	}
	return !1;
}
function Jn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(q !== null && q.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Jn(a, t, !1) : t === a && (n ? O(a, y) : a.f & 1024 && O(a, b), Ut(a));
	}
}
function Yn(e) {
	var t = J, n = Y, r = X, i = H, a = q, o = E, s = U, c = Wn, l = e.f;
	J = null, Y = 0, X = null, H = l & 96 ? null : e, q = null, Ke(e.ctx), U = !1, Wn = ++Un, e.ac !== null && (lt(() => {
		e.ac.abort(xe);
	}), e.ac = null);
	try {
		e.f |= ue;
		var u = e.fn, d = u();
		e.f |= ae;
		var f = e.deps, p = k?.is_fork;
		if (J !== null) {
			var m;
			if (p || Zn(e, Y), f !== null && Y > 0) for (f.length = Y + J.length, m = 0; m < J.length; m++) f[Y + m] = J[m];
			else e.deps = f = J;
			if (hn() && e.f & 512) for (m = Y; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && Y < f.length && (Zn(e, Y), f.length = Y);
		if (Ye() && X !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < X.length; m++) Jn(X[m], e);
		if (i !== null && i !== e) {
			if (Un++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Un;
			if (t !== null) for (let e of t) e.rv = Un;
			X !== null && (r === null ? r = X : r.push(...X));
		}
		return e.f & 8388608 && (e.f ^= fe), d;
	} catch (e) {
		return $e(e);
	} finally {
		e.f ^= ue, J = t, Y = n, X = r, H = i, q = a, Ke(o), U = s, Wn = c;
	}
}
function Xn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (J === null || !s.call(J, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512, c.f &= ~le), c.v !== r && nt(c), c.ac !== null && lt(() => {
			c.ac.abort(xe), c.ac = null, O(c, y);
		}), Et(c), Zn(c, 0);
	}
}
function Zn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Xn(e, n[r]);
}
function Qn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		O(e, v);
		var n = G, r = Rn;
		G = e, Rn = (t & 96) == 0;
		try {
			t & 16777232 ? kn(e) : On(e), Dn(e);
			var i = Yn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Hn;
		} finally {
			Rn = r, G = n;
		}
	}
}
async function $n() {
	await Promise.resolve(), Rt();
}
function Z(e) {
	var t = (e.f & 2) != 0;
	if (Ln?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (q === null || !q.has(e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Un && (e.rv = Un, J === null && n !== null && n[Y] === e ? Y++ : J === null ? J = [e] : J.push(e));
		else {
			H.deps ??= [], s.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : s.call(r, H) || r.push(H);
		}
	}
	if (V && qt.has(e)) return qt.get(e);
	if (t) {
		var i = e;
		if (V) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || tr(i)) && (a = wt(i)), qt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !U && H !== null && (Rn || (H.f & 512) != 0), c = (i.f & ae) === 0;
		qn(i) && (o && (i.f |= 512), Tt(i)), o && !c && (Dt(i), er(i));
	}
	if (A?.has(e)) return A.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function er(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Dt(t), er(t));
}
function tr(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (qt.has(t) || t.f & 2 && tr(t)) return !0;
	return !1;
}
function nr(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function rr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (pe in e) ir(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && pe in n && ir(n);
		}
	}
}
function ir(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			ir(e[n], t);
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
var ar = Symbol("events"), or = /* @__PURE__ */ new Set(), sr = /* @__PURE__ */ new Set();
function cr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || dr.call(t, e), !e.cancelBubble) return lt(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? D(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function lr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = cr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && gn(() => {
		t.removeEventListener(e, o, a);
	});
}
var ur = null;
function dr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	ur = e;
	var o = 0, s = ur === e && e[ar];
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
		u(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var d = H, f = G;
		W(null), K(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[ar]?.[r];
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
			e[ar] = t, delete e.currentTarget, W(d), K(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var fr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function pr(e) {
	return fr?.createHTML(e) ?? e;
}
function mr(e) {
	var t = dn("template");
	return t.innerHTML = pr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function hr(e, t) {
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
		if (S) return hr(C, null), C;
		i === void 0 && (i = mr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ cn(i)));
		var t = r || nn ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ cn(t), s = t.lastChild;
			hr(o, s);
		} else hr(t, t);
		return t;
	};
}
function $(e, t) {
	if (S) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = C), ze();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var gr = ["touchstart", "touchmove"];
function _r(e) {
	return gr.includes(e);
}
function vr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ye] ??= e.nodeValue) && (e[ye] = n, e.nodeValue = `${n}`);
}
function yr(e, t) {
	return Sr(e, t);
}
function br(e, t) {
	on(), t.intro = t.intro ?? !1;
	let r = t.target, i = S, a = C;
	try {
		for (var o = /* @__PURE__ */ cn(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ F(o);
		if (!o) throw n;
		Re(!0), w(o);
		let i = Sr(e, {
			...t,
			anchor: o
		});
		return Re(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && ke(), on(), ln(r), Re(!1), yr(e, t);
	} finally {
		Re(i), w(a);
	}
}
var xr = /* @__PURE__ */ new Map();
function Sr(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	on();
	var u = void 0, d = xn(() => {
		var s = r ?? t.appendChild(sn());
		pt(s, { pending: () => {} }, (t) => {
			qe({});
			var r = E;
			if (o && (r.c = o), a && (i.$$events = a), S && hr(t, null), u = e(t, i) || {}, S && (G.nodes.end = C, C === null || C.nodeType !== 8 || C.data !== "]")) throw Ie(), n;
			Je();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = _r(r);
					for (let e of [t, document]) {
						var a = xr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), xr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, dr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(or)), sr.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = xr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, dr), n.delete(e), n.size === 0 && xr.delete(r)) : n.set(e, i);
			}
			sr.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return Cr.set(u, d), u;
}
var Cr = /* @__PURE__ */ new WeakMap();
function wr(e, t) {
	let n = Cr.get(e);
	return n ? (Cr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Tr = class {
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
			if (n) Pn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Pn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
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
						In(r, t), t.append(sn()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Mn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = k, r = un();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = sn();
			i.append(a), this.#n.set(e, {
				effect: z(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, z(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else S && (this.anchor = C), this.#a(n);
	}
};
function Er(t) {
	E === null && Ce("onMount"), e && E.l !== null ? Dr(E).m.push(t) : _n(() => {
		let e = nr(t);
		if (typeof e == "function") return e;
	});
}
function Dr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Or(e, t, n = !1) {
	var r;
	S && (r = C, ze());
	var i = new Tr(e), a = n ? se : 0;
	function o(e, t) {
		if (S) {
			var n = He(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ve();
				w(a), i.anchor = a, Re(!1), i.ensure(e, t), Re(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	En(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function kr(e, t) {
	Sn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = dn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Ar = Symbol("is custom element"), jr = Symbol("is html"), Mr = Se ? "link" : "LINK";
function Nr(e) {
	if (S) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Pr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Pr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[be] = n, D(n), ct();
	}
}
function Pr(e, t, n, r) {
	var i = Fr(e);
	S && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Mr) || i[t] !== (i[t] = n) && (t === "loading" && (e[he] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Lr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Fr(e) {
	return e[ge] ??= {
		[Ar]: e.nodeName.includes("-"),
		[jr]: e.namespaceURI === i
	};
}
var Ir = /* @__PURE__ */ new Map();
function Lr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Ir.get(t);
	if (n) return n;
	Ir.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = h(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Rr(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	ut(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = zr(e) ? Br(a) : a, n(a), k !== null && r.add(k), await $n(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (S && e.defaultValue !== e.value || nr(t) == null && e.value) && (n(zr(e) ? Br(e.value) : e.value), k !== null && r.add(k)), wn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = k;
			if (r.has(i)) return;
		}
		zr(e) && n === Br(e.value) || e.type === "date" && !n && !e.value || n !== e.value && (e.value = n ?? "");
	});
}
function zr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Br(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Vr(e = !1) {
	let t = E, n = t.l.u;
	if (!n) return;
	let r = () => rr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ yt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Z(i);
	}
	n.b.length && yn(() => {
		Hr(t, r), ne(n.b);
	}), _n(() => {
		let e = nr(() => n.m.map(te));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && _n(() => {
		Hr(t, r), ne(n.a);
	});
}
function Hr(e, t) {
	if (e.l.s) for (let t of e.l.s) Z(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function Ur(t, n, r, i) {
	var a = !e || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ yt(i), Z(u)) : (l && (l = !1, c = s ? nr(i) : i), c);
	let p;
	if (o) {
		var m = pe in t || me in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, ee = !1;
	o ? [h, ee] = ot(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && Ae(n), p(h)));
	var g = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return g;
	if (p) {
		var te = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || te || ee) && p(t ? g() : e), e) : g();
		});
	}
	var ne = !1, _ = (r & 1 ? yt : St)(() => (ne = !1, g()));
	o && Z(_);
	var v = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(_) : a && o ? en(e) : e;
			return P(_, n), ne = !0, c !== void 0 && (c = n), e;
		}
		return V && ne || v.f & 16384 ? _.v : Z(_);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function Wr(e) {
	return new Gr(e);
}
var Gr = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ N(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Z(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === me ? !0 : (Z(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return P(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? br : yr)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), (!e?.props?.$$host || e.sync === !1) && Rt(), this.#e = r.$$events;
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
			wr(this.#t);
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
}, Kr;
typeof HTMLElement == "function" && (Kr = class extends HTMLElement {
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
					let n = dn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Jr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = qr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Wr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = bn(() => {
				wn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = qr(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = qr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function qr(e, t, n, r) {
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
function Jr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Yr(e, t, n, r, i, a) {
	let o = class extends Kr {
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
				n = qr(e, n, t), this.$$d[e] = n;
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
//#region PlexCard.svelte
var Xr = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-lueg2f\">Active</span>"), Zr = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Authenticated</span>"), Qr = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Connected</span>"), $r = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-lueg2f\">Disconnected</span>"), ei = /* @__PURE__ */ Q("<div class=\"loading-state svelte-lueg2f\"><div class=\"spinner svelte-lueg2f\"></div> <span>Linking with Plex Nexus...</span></div>"), ti = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\"> </button>"), ni = /* @__PURE__ */ Q("<button class=\"btn-ghost accent svelte-lueg2f\"> </button>"), ri = /* @__PURE__ */ Q("<button class=\"btn-danger-ghost svelte-lueg2f\">Cancel Authorization</button>"), ii = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\">Switch Account</button>"), ai = /* @__PURE__ */ Q("<button class=\"btn-primary plex-btn svelte-lueg2f\"><svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"currentColor\"><path d=\"M12 0L9.33 6.67L2 9.33L7.33 14.67L6 22L12 18.67L18 22L16.67 14.67L22 9.33L14.67 6.67L12 0Z\"></path></svg> Sign in with Plex</button>"), oi = /* @__PURE__ */ Q("<div class=\"settings-section svelte-lueg2f\"><div class=\"form-grid svelte-lueg2f\"><div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Server Access URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:32400\" class=\"input-field svelte-lueg2f\"/> <span class=\"helper-text svelte-lueg2f\">Typically http://[IP]:32400. Use localhost if running natively.</span></div> <div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Friendly Name</span> <input type=\"text\" placeholder=\"e.g. Home Media\" class=\"input-field svelte-lueg2f\"/></div> <div class=\"actions-row svelte-lueg2f\"><button class=\"btn-primary svelte-lueg2f\"> </button> <!> <!> <div class=\"auth-box svelte-lueg2f\"><!></div></div></div></div>"), si = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-lueg2f\"><div class=\"card-header svelte-lueg2f\"><div class=\"header-left svelte-lueg2f\"><h2 class=\"card-title svelte-lueg2f\">Plex Media Server</h2> <div class=\"badges svelte-lueg2f\"><!> <!> <!></div></div> <button class=\"btn-ghost-small svelte-lueg2f\"> </button></div> <!></section>"), ci = {
	hash: "svelte-lueg2f",
	code: "\n  /* SHADOW DOM STYLING */.plugin-card.svelte-lueg2f {background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;color:var(--text-primary);font-family:inherit;}.card-header.svelte-lueg2f {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-lueg2f {display:flex;align-items:center;gap:16px;}.card-title.svelte-lueg2f {margin:0;font-size:18px;font-weight:700;letter-spacing:-0.01em;}.badges.svelte-lueg2f {display:flex;gap:8px;}.status-badge.svelte-lueg2f {font-size:9px;padding:2px 8px;border-radius:5px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;}.status-badge.active.svelte-lueg2f {background:rgba(20, 184, 166, 0.1);color:var(--color-primary);border:1px solid rgba(20, 184, 166, 0.2);}.status-badge.success.svelte-lueg2f {background:rgba(16, 185, 129, 0.1);color:#10b981;border:1px solid rgba(16, 185, 129, 0.2);}.status-badge.warning.svelte-lueg2f {background:rgba(245, 158, 11, 0.1);color:#f59e0b;border:1px solid rgba(245, 158, 11, 0.2);}.btn-ghost.svelte-lueg2f,\n  .btn-ghost-small.svelte-lueg2f,\n  .btn-danger-ghost.svelte-lueg2f {padding:10px 18px;background:rgba(255, 255, 255, 0.04);border:1px solid var(--border-subtle);color:var(--text-primary);border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-ghost-small.svelte-lueg2f {padding:6px 12px;font-size:11px;border-radius:6px;}.btn-ghost.svelte-lueg2f:hover,\n  .btn-ghost-small.svelte-lueg2f:hover {background:rgba(255, 255, 255, 0.08);border-color:rgba(255, 255, 255, 0.2);}.btn-ghost.accent.svelte-lueg2f {color:var(--color-primary);border-color:rgba(20, 184, 166, 0.3);}.btn-danger-ghost.svelte-lueg2f {color:#ef4444;border-color:rgba(239, 68, 68, 0.2);}.btn-primary.svelte-lueg2f {padding:10px 24px;background:var(--color-primary);color:#000;border:none;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-lueg2f:hover:not(:disabled) {filter:brightness(1.1);transform:translateY(-1px);}.plex-btn.svelte-lueg2f {display:flex;align-items:center;gap:8px;background:#e5a00d; /* Plex Gold */color:#000;}.loading-state.svelte-lueg2f {display:flex;flex-direction:column;align-items:center;gap:16px;padding:40px;color:var(--text-muted);}.spinner.svelte-lueg2f {width:28px;height:28px;border:3px solid rgba(255, 255, 255, 0.05);border-top-color:var(--color-primary);border-radius:50%;\n    animation: svelte-lueg2f-spin 1s linear infinite;}\n\n  @keyframes svelte-lueg2f-spin {\n    to {\n      transform: rotate(360deg);\n    }\n  }.settings-section.svelte-lueg2f {margin-top:8px;}.form-grid.svelte-lueg2f {display:flex;flex-direction:column;gap:20px;}.form-field.svelte-lueg2f {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-lueg2f {font-size:12px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;}.input-field.svelte-lueg2f {width:100%;padding:12px 16px;background:var(--bg-input, #0b0f1a);border:1px solid var(--border-subtle);border-radius:10px;color:var(--text-primary);font-size:14px;transition:all 0.2s;}.input-field.svelte-lueg2f:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 3px rgba(20, 184, 166, 0.1);}.helper-text.svelte-lueg2f {font-size:11px;color:var(--text-muted);font-style:italic;}.actions-row.svelte-lueg2f {display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:8px;}.auth-box.svelte-lueg2f {margin-left:auto;}\n\n  @media (max-width: 600px) {.auth-box.svelte-lueg2f {margin-left:0;width:100%;}.auth-box.svelte-lueg2f button:where(.svelte-lueg2f) {width:100%;}\n  }"
};
function li(e, t) {
	qe(t, !1), kr(e, ci);
	let n = Ur(t, "apiBase", 12, ""), r = /* @__PURE__ */ N(""), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(!1), o = /* @__PURE__ */ N(!1), s = /* @__PURE__ */ N(!0), c = /* @__PURE__ */ N(!1), l = /* @__PURE__ */ N(!1), u = /* @__PURE__ */ N(!1), d = null, f = null, p = /* @__PURE__ */ N(!1), m = /* @__PURE__ */ N(!1), h = /* @__PURE__ */ N(!1);
	Er(async () => {
		n(n().replace(/\/$/, "")), await g(), P(s, !1);
	});
	async function ee() {
		try {
			if (P(h, !0), !(await fetch(`${n()}/activate`, { method: "POST" })).ok) throw Error("Activation failed");
			await g();
		} catch (e) {
			console.error("Failed to activate server:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Activation failed. Check logs.",
				type: "error"
			} }));
		} finally {
			P(h, !1);
		}
	}
	async function g() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e?.settings && (P(r, e.settings.base_url || ""), P(i, e.settings.server_name || ""), P(a, e.settings.has_token || !1), P(o, e.settings.connected || !1), P(m, e.settings.is_active || !1));
		} catch (e) {
			console.error("Failed to load Plex settings:", e);
		}
	}
	async function te() {
		if (!Z(r).trim()) {
			window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Server URL is required",
				type: "error"
			} }));
			return;
		}
		try {
			if (P(c, !0), !(await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					base_url: Z(r),
					server_name: Z(i)
				})
			})).ok) throw Error("Save failed");
			await g(), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Settings saved successfully",
				type: "success"
			} }));
		} catch (e) {
			console.error("Failed to save Plex settings:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Failed to save settings.",
				type: "error"
			} }));
		} finally {
			P(c, !1);
		}
	}
	async function ne() {
		try {
			P(u, !0);
			let e = await (await fetch(`${n()}/auth/start`, { method: "POST" })).json();
			e?.oauth_url && e?.session_id && (d = e.session_id, window.open(e.oauth_url, "PlexOAuth", "width=600,height=700,menubar=no,status=no"), f = setInterval(async () => {
				try {
					(await (await fetch(`${n()}/auth/poll/${d}`)).json())?.completed && (clearInterval(f), f = null, P(u, !1), d = null, await g());
				} catch (e) {
					console.error("OAuth poll error:", e), e.status === 404 && (clearInterval(f), f = null, P(u, !1), d = null);
				}
			}, 3e3));
		} catch (e) {
			console.error("Failed to start Plex OAuth:", e), P(u, !1);
		}
	}
	async function _() {
		if (d && f) {
			clearInterval(f), f = null;
			try {
				await fetch(`${n()}/auth/cancel/${d}`, { method: "DELETE" });
			} catch (e) {
				console.error("Failed to cancel OAuth:", e);
			}
			d = null, P(u, !1);
		}
	}
	async function v() {
		try {
			P(l, !0), (await (await fetch(`${n()}/test-connection`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ base_url: Z(r) })
			})).json())?.connected ? (window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Connection successful!",
				type: "success"
			} })), await g()) : window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Connection failed. Check URL and ensure Plex is running.",
				type: "error"
			} }));
		} catch (e) {
			console.error("Connection test failed:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Test failed with error.",
				type: "error"
			} }));
		} finally {
			P(l, !1);
		}
	}
	var y = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Rt();
		}
	};
	Vr();
	var b = si(), re = I(b), ie = I(re), ae = L(I(ie), 2), oe = I(ae), se = (e) => {
		$(e, Xr());
	};
	Or(oe, (e) => {
		Z(m) && e(se);
	});
	var x = L(oe, 2), ce = (e) => {
		$(e, Zr());
	};
	Or(x, (e) => {
		Z(a) && e(ce);
	});
	var le = L(x, 2), ue = (e) => {
		$(e, Qr());
	}, de = (e) => {
		$(e, $r());
	};
	Or(le, (e) => {
		Z(o) ? e(ue) : Z(a) && e(de, 1);
	}), T(ae), T(ie);
	var fe = L(ie, 2), pe = I(fe, !0);
	T(fe), T(re);
	var me = L(re, 2), he = (e) => {
		$(e, ei());
	}, ge = (e) => {
		var t = oi(), n = I(t), o = I(n), s = L(I(o), 2);
		Nr(s), Be(2), T(o);
		var d = L(o, 2), f = L(I(d), 2);
		Nr(f), T(d);
		var p = L(d, 2), g = I(p), y = I(g, !0);
		T(g);
		var b = L(g, 2), re = (e) => {
			var t = ti(), n = I(t, !0);
			T(t), Tn((e) => {
				t.disabled = e, vr(n, Z(l) ? "Testing..." : "Test Connection");
			}, [() => (Z(l), Z(r), nr(() => Z(l) || !Z(r).trim()))]), lr("click", t, v), $(e, t);
		};
		Or(b, (e) => {
			Z(a) && e(re);
		});
		var ie = L(b, 2), ae = (e) => {
			var t = ni(), n = I(t, !0);
			T(t), Tn(() => {
				t.disabled = Z(h), vr(n, Z(h) ? "Activating..." : "Activate for Sync");
			}), lr("click", t, ee), $(e, t);
		};
		Or(ie, (e) => {
			!Z(m) && Z(a) && e(ae);
		});
		var oe = L(ie, 2), se = I(oe), x = (e) => {
			var t = ri();
			lr("click", t, _), $(e, t);
		}, ce = (e) => {
			var t = ii();
			lr("click", t, ne), $(e, t);
		}, le = (e) => {
			var t = ai();
			lr("click", t, ne), $(e, t);
		};
		Or(se, (e) => {
			Z(u) ? e(x) : Z(a) ? e(ce, 1) : e(le, -1);
		}), T(oe), T(p), T(n), T(t), Tn(() => {
			g.disabled = Z(c), vr(y, Z(c) ? "Saving..." : "Save Configuration");
		}), Rr(s, () => Z(r), (e) => P(r, e)), Rr(f, () => Z(i), (e) => P(i, e)), lr("click", g, te), $(e, t);
	};
	return Or(me, (e) => {
		Z(s) ? e(he) : Z(p) || e(ge, 1);
	}), T(b), Tn(() => vr(pe, Z(p) ? "Expand" : "Collapse")), lr("click", fe, () => P(p, !Z(p))), $(e, b), Je(y);
}
customElements.define("plex-dashboard-card", Yr(li, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { li as default };
